"""Compara classificadores PÚBLICOS de prompt injection no protocolo do guard: página, frase e latência.

    python bench/paginas/construir.py                                    (uma vez: monta work/paginas.json)
    python bench/baselines.py avaliar MODELO ATAQUE --janela 1300 --sobra 200 --max-length 512
                                  [--paginas work/paginas.json] [--saida res.json] [--nome rotulo] [--trechos]
    python bench/baselines.py tabela res1.json res2.json ... > baselines.md
    python bench/baselines.py latencia res1.json ...        (remede com a máquina ociosa)
    python bench/baselines.py juntar baselines.json res1.json ... [--indisponivel "id=motivo"]

MODELO é um id do Hugging Face ou uma pasta local; ATAQUE é o rótulo de ataque do id2label do modelo
(vários separados por vírgula somam as probabilidades, p.ex. Prompt Guard v1 "INJECTION,JAILBREAK").
Uma pasta com ptguard.json (ou laya-classificador.json, o nome antigo) aplica o prefixo e a temperatura
dela; o nosso e5-large usa "query: " e T = 1,0.

Página (a unidade em que o hook decide): as 217 páginas benignas e 60 com injeção que
bench/paginas/construir.py remonta da fonte e confere por hash, para todos os modelos verem exatamente
o mesmo texto. Janela = o que cabe no max_length do modelo;
decisão da página = máximo das janelas. Frase: Weni/prompt-injections-1.0.0 (train, todo positivo,
pt-BR nativo) e xTRam1/safe-guard-prompt-injection (test). Latência por janela na CPU onde roda.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import List, Sequence

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from ptguard.classificador import ler_meta  # noqa: E402
from ptguard.metrics import wilson  # noqa: E402
from ptguard.paginas import pedacos  # noqa: E402

PAGINAS = RAIZ / "work" / "paginas.json"
LIMIARES = (0.5, 0.9, 0.95, 0.99, 0.999)
AVISO_FALSO_ALVO = 0.02            # critério para ligar o hook (fixado antes da medição; ver o artigo)
LOTE = 16
AMOSTRA_LATENCIA = 40


def md5_textos(textos: Sequence[str]) -> str:
    return hashlib.md5("\x1e".join(textos).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- modelo

def revisao_do_hub(ref: str):
    """Commit do Hub que está no cache (refs/main); pasta local não tem revisão do Hub."""
    if Path(ref).exists():
        return "local"
    from huggingface_hub import constants
    arq = Path(constants.HF_HUB_CACHE) / ("models--" + ref.replace("/", "--")) / "refs" / "main"
    return arq.read_text(encoding="utf-8").strip() if arq.exists() else None


class Modelo:
    def __init__(self, ref: str, max_length: int, ataque: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(int(os.environ.get("PTGUARD_THREADS", os.cpu_count() or 1)))
        meta = ler_meta(ref) if Path(ref).exists() else {}      # modelo do Hub: sem prefixo, T = 1
        self.prefixo = meta.get("prefixo", "")
        self.temperatura = float(meta.get("temperatura", 1.0))
        self.max_length = max_length
        from ptguard.config import revisao
        fixada = None if Path(ref).exists() else revisao(ref)   # modelo do Hub: a revisão de ptguard/revisoes.json
        self.tok = AutoTokenizer.from_pretrained(ref, revision=fixada)
        self.model = AutoModelForSequenceClassification.from_pretrained(ref, revision=fixada, dtype=torch.float32).eval()
        self.labels = [str(self.model.config.id2label[i]) for i in range(self.model.config.num_labels)]
        self.idx = self._indices(ataque)
        self.revisao = fixada or revisao_do_hub(ref)
        self._torch = torch

    def _indices(self, ataque: str) -> List[int]:
        pedidos = [a.strip().lower() for a in ataque.split(",") if a.strip()]
        achados = [i for i, nome in enumerate(self.labels) if nome.lower() in pedidos]
        if len(achados) != len(pedidos):
            raise SystemExit(f"rótulo de ataque {ataque!r} não está em id2label {self.labels}")
        return achados

    def _lote(self, textos: Sequence[str]) -> np.ndarray:
        """Log-odds do ataque, log P(ataque) - log P(resto): ordena sem saturar onde P já arredonda para 1."""
        with self._torch.inference_mode():
            enc = self.tok([self.prefixo + t for t in textos], padding=True, truncation=True,
                           max_length=self.max_length, return_tensors="pt")
            z = self.model(**enc).logits.float().numpy().astype(np.float64) / self.temperatura
        ataque = np.logaddexp.reduce(z[:, self.idx], axis=1)
        resto = np.logaddexp.reduce(np.delete(z, self.idx, axis=1), axis=1)
        return ataque - resto

    def log_odds(self, textos: Sequence[str], lote: int = LOTE) -> np.ndarray:
        """Do menor para o maior texto, em lotes (lote misturado paga padding até o maior)."""
        textos = list(textos)
        ordem = sorted(range(len(textos)), key=lambda i: len(textos[i]))
        out = np.zeros(len(textos), dtype=np.float64)
        for ini in range(0, len(ordem), lote):
            idx = ordem[ini:ini + lote]
            out[idx] = self._lote([textos[i] for i in idx])
        return out

    def n_tokens(self, textos: Sequence[str]) -> np.ndarray:
        enc = self.tok([self.prefixo + t for t in textos], truncation=False)
        return np.array([len(ids) for ids in enc["input_ids"]])


# ---------------------------------------------------------------- métricas

def auroc(neg: Sequence[float], pos: Sequence[float]) -> float:
    """P(score de positivo > score de negativo), empate vale meio (Mann-Whitney)."""
    n, p = np.asarray(neg)[None, :], np.asarray(pos)[:, None]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (n.size * p.size))


def prob(log_odds) -> np.ndarray:
    with np.errstate(over="ignore"):
        return 1.0 / (1.0 + np.exp(-np.asarray(log_odds, dtype=np.float64)))


def taxa(log_odds: Sequence[float], limiar: float) -> float:
    """Fração com P(ataque) >= limiar."""
    v = np.asarray(log_odds)
    return float((prob(v) >= limiar).mean()) if v.size else float("nan")


def ponto_de_operacao(benignas: np.ndarray, com_inj: np.ndarray, alvo: float = AVISO_FALSO_ALVO) -> dict:
    """Menor corte (em log-odds) com aviso falso <= alvo, decisão ESTRITAMENTE acima dele, e a detecção nele."""
    permitidos = int(np.floor(alvo * len(benignas)))
    corte = float(np.sort(benignas)[::-1][permitidos])
    return {"alvo_aviso_falso": alvo, "corte_log_odds": corte, "corte_1_menos_p": float(1 / (1 + np.exp(corte))),
            "aviso_falso": float((benignas > corte).mean()), "deteccao": float((com_inj > corte).mean())}


# ---------------------------------------------------------------- avaliação

def janelas_de(paginas: List[dict], janela: int, sobra: int):
    textos, dono = [], []
    for i, pg in enumerate(paginas):
        for j in pedacos(pg["texto"], janela, sobra):
            textos.append(j)
            dono.append(i)
    return textos, np.array(dono)


def pior_por_pagina(probs: np.ndarray, dono: np.ndarray, n: int):
    pior, onde = np.zeros(n), np.full(n, -1)
    for k, (i, pr) in enumerate(zip(dono, probs)):
        if pr > pior[i] or onde[i] < 0:
            pior[i], onde[i] = pr, k
    return pior, onde


def avaliar_paginas(m: Modelo, paginas: dict, janela: int, sobra: int, trechos: bool = False) -> dict:
    ben, inj = paginas["benignas"], paginas["com_injecao"]
    tb, db = janelas_de(ben, janela, sobra)
    ti, di = janelas_de(inj, janela, sobra)
    t0 = time.perf_counter()
    pb = m.log_odds(tb)
    pi = m.log_odds(ti)
    segundos = time.perf_counter() - t0
    pior_b, onde_b = pior_por_pagina(pb, db, len(ben))
    pior_i, _ = pior_por_pagina(pi, di, len(inj))
    toks = m.n_tokens(tb + ti)
    fonte = np.array([x["fonte"] for x in inj])
    por_limiar = {}
    for lim in LIMIARES:
        por_limiar[str(lim)] = {"aviso_falso": taxa(pior_b, lim), "deteccao": taxa(pior_i, lim),
                                "deteccao_weni": taxa(pior_i[fonte == "weni"], lim),
                                "deteccao_xtram1": taxa(pior_i[fonte == "xtram1"], lim),
                                "janelas_benignas_acima": taxa(pb, lim),
                                "aviso_falso_ic95": wilson(int((prob(pior_b) >= lim).sum()), len(pior_b)),
                                "deteccao_ic95": wilson(int((prob(pior_i) >= lim).sum()), len(pior_i))}
    topo = np.argsort(-pior_b)[:5]
    return {"n_benignas": len(ben), "n_com_injecao": len(inj), "n_janelas": len(tb) + len(ti),
            "tokens_por_janela": {"p50": float(np.median(toks)), "p90": float(np.percentile(toks, 90)),
                                  "max": int(toks.max()), "truncadas": float((toks > m.max_length).mean())},
            "por_limiar": por_limiar, "auroc_pagina": auroc(pior_b, pior_i),
            "ponto_aviso_falso_2pct": ponto_de_operacao(pior_b, pior_i),
            "media_p_pagina_benigna": float(prob(pior_b).mean()),
            "mediana_p_janela_benigna": float(np.median(prob(pb))),
            "ms_por_janela_em_lote": 1000 * segundos / (len(tb) + len(ti)),
            # o trecho é texto de README de terceiro: só com --trechos (os resultados publicados não têm)
            "benignas_mais_suspeitas": [{"pacote": ben[i]["pacote"], "log_odds": round(float(pior_b[i]), 3),
                                         "janela": int(onde_b[i] - np.flatnonzero(db == i)[0]),
                                         **({"trecho": tb[onde_b[i]][:300]} if trechos else {})} for i in topo],
            "log_odds_benignas": [round(float(x), 3) for x in pior_b],
            "log_odds_com_injecao": [round(float(x), 3) for x in pior_i]}


def frases_abertas():
    from datasets import load_dataset
    from ptguard.config import revisao
    weni_repo, xt_repo = "Weni/prompt-injections-1.0.0", "xTRam1/safe-guard-prompt-injection"
    weni = [str(r["text"]) for r in load_dataset(weni_repo, revision=revisao(weni_repo))["train"] if r.get("text")]
    xt = load_dataset(xt_repo, revision=revisao(xt_repo))["test"]
    return weni, [str(r["text"]) for r in xt], np.array([int(r["label"]) for r in xt])


def avaliar_frases(m: Modelo) -> dict:
    weni, xt, y = frases_abertas()
    pw, px = m.log_odds(weni), m.log_odds(xt)
    pred = px >= 0.0                      # P >= 0,5
    return {"weni": {"n": len(weni), "md5": md5_textos(weni), "deteccao_0.5": taxa(pw, 0.5),
                     "deteccao_0.9": taxa(pw, 0.9)},
            "xtram1": {"n": len(xt), "md5": md5_textos(xt), "positivos": int(y.sum()),
                       "acuracia_0.5": float((pred == (y == 1)).mean()), "tpr_0.5": taxa(px[y == 1], 0.5),
                       "fpr_0.5": taxa(px[y == 0], 0.5), "auroc": auroc(px[y == 0], px[y == 1])},
            "log_odds_weni": [round(float(x), 3) for x in pw],
            "log_odds_xtram1": [round(float(x), 3) for x in px], "y_xtram1": y.tolist()}


def latencia(m: Modelo, paginas: dict, janela: int, sobra: int) -> dict:
    """Janela cheia (a 1ª de cada página: toda página tem > 1500 chars), após 3 de aquecimento:
    uma por chamada (o caso do hook com página curta) e em lotes de LOTE (página longa)."""
    amostra = [pedacos(pg["texto"], janela, sobra)[0] for pg in paginas["benignas"][:4 * LOTE]]
    for t in amostra[:3]:
        m.log_odds([t], lote=1)
    carga_antes = os.getloadavg() if hasattr(os, "getloadavg") else None
    ms = []
    for t in amostra[:AMOSTRA_LATENCIA]:
        t0 = time.perf_counter()
        m.log_odds([t], lote=1)
        ms.append(1000 * (time.perf_counter() - t0))
    t0 = time.perf_counter()
    m.log_odds(amostra, lote=LOTE)
    lote_ms = 1000 * (time.perf_counter() - t0) / len(amostra)
    return {"n": len(ms), "media_ms": float(np.mean(ms)), "p50_ms": float(np.median(ms)),
            "p90_ms": float(np.percentile(ms, 90)), "lote_ms_por_janela": lote_ms, "lote": LOTE,
            "n_lote": len(amostra), "threads": m._torch.get_num_threads(),
            "carga_1min_antes": carga_antes[0] if carga_antes else None,
            "carga_1min_depois": os.getloadavg()[0] if carga_antes else None}


def avaliar(a: argparse.Namespace) -> None:
    logging.getLogger("transformers").setLevel(logging.ERROR)
    paginas = json.loads(Path(a.paginas).read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    m = Modelo(a.modelo, a.max_length, a.ataque)
    res = {"nome": a.nome or Path(a.modelo).name, "modelo": a.modelo, "revisao": m.revisao,
           "rotulos": m.labels, "ataque": [m.labels[i] for i in m.idx], "prefixo": m.prefixo,
           "temperatura": m.temperatura, "max_length": a.max_length, "janela": a.janela, "sobra": a.sobra,
           "md5_injecoes_paginas": paginas.get("md5_injecoes"), "data": date.today().isoformat(),
           "maquina": os.uname().machine if hasattr(os, "uname") else sys.platform}
    print(f"[{res['nome']}] páginas {a.janela}/{a.sobra} @ {a.max_length} tokens", file=sys.stderr, flush=True)
    res["pagina"] = avaliar_paginas(m, paginas, a.janela, a.sobra, a.trechos)
    if not a.sem_frases:
        print(f"[{res['nome']}] frases", file=sys.stderr, flush=True)
        res["frase"] = avaliar_frases(m)
    res["latencia"] = latencia(m, paginas, a.janela, a.sobra)
    res["segundos_total"] = time.perf_counter() - t0
    saida = Path(a.saida or f"baseline-{res['nome']}-{a.janela}.json")
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    pl = res["pagina"]["por_limiar"]
    print(f"[{res['nome']}] aviso falso " + " ".join(f"{k}:{v['aviso_falso']:.1%}" for k, v in pl.items())
          + f" | {res['segundos_total']:.0f}s -> {saida}", file=sys.stderr, flush=True)


def remedir_latencia(arquivo: Path, paginas_json: Path = PAGINAS) -> None:
    """Mede de novo a latência de um resultado (máquina ociosa) e guarda a medida anterior ao lado."""
    logging.getLogger("transformers").setLevel(logging.ERROR)
    res = json.loads(arquivo.read_text(encoding="utf-8"))
    paginas = json.loads(Path(paginas_json).read_text(encoding="utf-8"))
    m = Modelo(res["modelo"], res["max_length"], ",".join(res["ataque"]))
    res.setdefault("latencia_sob_carga", res["latencia"])
    res["latencia"] = latencia(m, paginas, res["janela"], res["sobra"])
    arquivo.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"[{res['nome']}] {res['latencia']['media_ms']:.0f} ms/janela", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- tabela

def pct(x: float, casas: int = 1) -> str:
    return "—" if x is None or x != x else f"{100 * x:.{casas}f}%".replace(".", ",")


def num(x: float, casas: int = 3) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def corte_p(op: dict) -> str:
    """P do corte; perto de 1 escreve 1−ε (a probabilidade já não distingue nada ali)."""
    resto = op["corte_1_menos_p"]
    return num(1 - resto) if resto >= 1e-3 else "1−" + f"{resto:.0e}".replace("e-0", "e-")


def _linha_pagina(r: dict) -> str:
    pg, celulas = r["pagina"], []
    for lim in ("0.5", "0.9", "0.95", "0.99"):
        v = pg["por_limiar"][lim]
        celulas.append(f"{pct(v['aviso_falso'])} / {pct(v['deteccao'], 0)} "
                       f"({pct(v['deteccao_weni'], 0)}\\|{pct(v['deteccao_xtram1'], 0)})")
    op = pg["ponto_aviso_falso_2pct"]
    return (f"| {r['nome']} | {r['janela']}/{r['sobra']} @ {r['max_length']} | {pct(pg['tokens_por_janela']['truncadas'])} | "
            + " | ".join(celulas) + f" | {num(pg['auroc_pagina'])} | {pct(op['deteccao'], 0)} (P > {corte_p(op)}) |")


def _linha_frase(r: dict) -> str:
    f, lat = r.get("frase"), r["latencia"]
    lote = lat.get("lote_ms_por_janela", r["pagina"]["ms_por_janela_em_lote"])
    if not f:
        return f"| {r['nome']} | — | — | — | — | — | {lat['media_ms']:.0f} | {lote:.0f} |"
    w, x = f["weni"], f["xtram1"]
    return (f"| {r['nome']} | {pct(w['deteccao_0.5'])} | {pct(x['acuracia_0.5'])} | {pct(x['tpr_0.5'])} | "
            f"{pct(x['fpr_0.5'])} | {num(x['auroc'])} | {lat['media_ms']:.0f} | {lote:.0f} |")


def tabela(arquivos: List[str]) -> str:
    rs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in arquivos]
    cab = ("| Modelo | Janela/sobra @ max_length | Janelas truncadas | "
           + " | ".join(f"AF / Det (Weni\\|xTRam1) @ {lim}" for lim in ("0,5", "0,9", "0,95", "0,99"))
           + " | AUROC página | Det. com AF ≤ 2% |")
    sep = "|" + "---|" * (cab.replace("\\|", "").count("|") - 1)    # "\|" é barra dentro da célula
    linhas = ["### Página (217 benignas, 60 com injeção; decisão = máximo das janelas)", "", cab, sep]
    linhas += [_linha_pagina(r) for r in rs]
    linhas += ["", "AF = aviso falso em página benigna; Det = detecção em página com injeção.", "",
               "### Frase e latência", "",
               "| Modelo | Weni det. @0,5 | xTRam1 acurácia @0,5 | xTRam1 TPR | xTRam1 FPR | xTRam1 AUROC | "
               "ms/janela (1 por chamada) | ms/janela (lote 16) |", "|---|---|---|---|---|---|---|---|"]
    linhas += [_linha_frase(r) for r in rs]
    return "\n".join(linhas) + "\n"


def juntar(saida: Path, arquivos: List[str], indisponiveis: List[str], notas: List[str]) -> None:
    """Um JSON só, na ordem dada: rodadas com frase (protocolo principal) e só página (controle de janela)."""
    rs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in arquivos]
    par = lambda x: [c.strip() for c in (x.split("=", 1) + [""])[:2]]
    dados = {"script": "bench/baselines.py", "paginas": "bench/paginas/manifesto.jsonl (remontadas por construir.py)",
             **{k: v for k, v in map(par, notas)},
             "indisponiveis": [dict(zip(("modelo", "motivo"), par(x))) for x in indisponiveis],
             "principais": [r for r in rs if r.get("frase")], "controle": [r for r in rs if not r.get("frase")]}
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{len(dados['principais'])} principais, {len(dados['controle'])} de controle -> {saida}", file=sys.stderr)


# ---------------------------------------------------------------- CLI

def main() -> None:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    av = sub.add_parser("avaliar")
    av.add_argument("modelo")
    av.add_argument("ataque")
    av.add_argument("--janela", type=int, required=True)
    av.add_argument("--sobra", type=int, required=True)
    av.add_argument("--max-length", type=int, required=True)
    av.add_argument("--paginas", default=str(PAGINAS))
    av.add_argument("--saida")
    av.add_argument("--nome")
    av.add_argument("--sem-frases", action="store_true", help="só página (rodada de controle)")
    av.add_argument("--trechos", action="store_true",
                    help="grava 300 chars das janelas benignas mais suspeitas (texto de terceiro: não publique)")
    tb = sub.add_parser("tabela")
    tb.add_argument("arquivos", nargs="+")
    la = sub.add_parser("latencia", help="remede a latência de resultados já gravados (máquina ociosa)")
    la.add_argument("arquivos", nargs="+")
    la.add_argument("--paginas", default=str(PAGINAS))
    ju = sub.add_parser("juntar", help="junta resultados num JSON só")
    ju.add_argument("saida")
    ju.add_argument("arquivos", nargs="+")
    ju.add_argument("--indisponivel", action="append", default=[], help='"modelo=motivo" (repetível)')
    ju.add_argument("--nota", action="append", default=[], help='"chave=valor" de metadado (repetível)')
    a = ap.parse_args()
    if a.cmd == "avaliar":
        avaliar(a)
    elif a.cmd == "latencia":
        for arq in a.arquivos:
            remedir_latencia(Path(arq), Path(a.paginas))
    elif a.cmd == "juntar":
        juntar(Path(a.saida), a.arquivos, a.indisponivel, a.nota)
    else:
        sys.stdout.write(tabela(a.arquivos))


if __name__ == "__main__":
    main()
