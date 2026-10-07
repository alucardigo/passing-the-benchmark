"""Compara duas versões do guard (v3 x v6) nos testes de frase e na avaliação por página.

    python analysis/comparar_versoes.py \
        --base prompt_injection-e5large --nova prompt_injection-e5large-v6 \
        --res-base results/runs/guard-prompt_injection-e5large-AAAA.json \
        --res-nova results/runs/guard-prompt_injection-e5large-v6-AAAA.json \
        --pag-base .cache/probs/guard-paginas-640-160-prompt_injection-e5large.json \
        --pag-nova .cache/probs/guard-paginas-640-160-prompt_injection-e5large-v6.json \
        --saida results/v6/v6

Entrada: P(injeção) por item gravada por `pipeline/treinar.py avaliar` (<cache>/probs/<modelo>/<teste>.npy,
com o gabarito em .gold.npy) e o JSON de bench/paginas/avaliar.py. Tudo público (bases abertas e
descrições de pacotes). Os dados por item da comparação do artigo estão em results/v6/dados/.
Saída: <saida>.json (números) e <saida>-tabelas.md (tabelas, embutidas no texto <saida>.md). Intervalo de Wilson 95%; comparação pareada por
McNemar exato (mesmos itens, mesma ordem), porque os dois modelos veem exatamente os mesmos textos.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from ptguard.config import CACHE  # noqa: E402

PROBS = CACHE / "probs"
LIMIARES = (0.5, 0.9, 0.95, 0.99, 0.999)
ALVO_AVISO_FALSO = 0.02

# ordem e papel de cada teste na tabela (o que ele mede)
PAPEL = {
    "weni": "injeção pt-BR nativa (HackAPrompt traduzida), fora da distribuição",
    "xtram1": "injeção/benigno en, fora da distribuição",
    "xtram1-pt": "xTRam1 traduzido (Opus-MT)",
    "massive_pt": "benigno pt (comandos a assistente)",
    "dolly": "benigno en (instruções a assistente)",
    "dolly-pt": "Dolly traduzido",
    "deepset": "deepset en (teste oficial)",
    "deepset-pt": "deepset traduzido",
    "jackhhao": "jailbreak en (teste oficial)",
    "jackhhao-pt": "jackhhao traduzido",
    "spml": "SPML en (20% por hash)",
    "spml-pt": "SPML traduzido",
    "rikka": "multilíngue (teste oficial)",
    "shieldlm": "ShieldLM (teste oficial)",
    "yanis": "injeções (20% por hash)",
    "so_perguntas": "benigno técnico: perguntas do StackOverflow (20% por hash)",
    "so_respostas": "benigno técnico: respostas do StackOverflow (20% por hash)",
    "docstrings": "benigno técnico: docstrings Python (20% por hash)",
    "fumaca": "fumaça pt-BR escrita à mão (10 frases)",
}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(max(0.0, centro - meia), 4), round(min(1.0, centro + meia), 4))


def mcnemar_exato(b: int, c: int) -> float:
    """p bilateral: b = só a base acerta, c = só a nova acerta."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cauda = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return float(min(1.0, 2 * cauda))


def carregar_probs(modelos: str, teste: str):
    """`modelos`: pastas sob <cache>/probs separadas por vírgula (a primeira que tiver o teste vale)."""
    for modelo in modelos.split(","):
        p, g = PROBS / modelo / f"{teste}.npy", PROBS / modelo / f"{teste}.gold.npy"
        if p.exists() and g.exists():
            return np.load(p), np.load(g).astype(bool)
    return None, None


def juntar_resultados(arquivos: str) -> dict:
    """Vários JSON de `--avaliar` (vírgula) num só: os testes se somam; o último arquivo vence."""
    res = {"teste": {}, "arquivos": []}
    for a in arquivos.split(","):
        d = json.loads(Path(a).read_text(encoding="utf-8"))
        res["teste"].update(d.get("teste", {}))
        res["arquivos"].append(Path(a).name)
    return res


def weni_limpo(base: str, nova: str, arq: Path, limiar: float = 0.9) -> dict:
    """Weni dividido pelo vizinho mais próximo (cosseno e5-base) entre os exemplos que só a v3 viu no treino."""
    m = np.array(json.loads(arq.read_text(encoding="utf-8"))["max_cos"])
    perto = m > limiar
    out = {"limiar_cosseno": limiar, "contaminados": int(perto.sum()), "limpos": int((~perto).sum())}
    pb, _ = carregar_probs(base, "weni")
    pn, _ = carregar_probs(nova, "weni")
    for nome, p in (("v3", pb), ("v6", pn)):
        if p is not None and len(p) == len(m):
            k = int((p[~perto] > 0.5).sum())
            out[nome] = {"contaminados": round(float((p[perto] > 0.5).mean()), 4),
                         "limpos": round(k / int((~perto).sum()), 4), "limpos_ic95": wilson(k, int((~perto).sum()))}
    if pb is not None and pn is not None and len(pb) == len(pn) == len(m):
        ab, an = pb[~perto] > 0.5, pn[~perto] > 0.5
        b, c = int((ab & ~an).sum()), int((~ab & an).sum())
        out["pareado_limpos"] = {"so_v3_acerta": b, "so_v6_acerta": c, "mcnemar_p": mcnemar_exato(b, c)}
    return out


def frases(base: str, nova: str, res_base: dict, res_nova: dict) -> dict:
    testes = [t for t in PAPEL if t in res_base.get("teste", {}) or t in res_nova.get("teste", {})]
    testes += [t for t in res_nova.get("teste", {}) if t not in testes]
    out = {}
    for t in testes:
        pb, gb = carregar_probs(base, t)
        pn, gn = carregar_probs(nova, t)
        linha = {"papel": PAPEL.get(t, "")}
        for nome, p, g, res in (("v3", pb, gb, res_base), ("v6", pn, gn, res_nova)):
            if p is None:
                continue
            acerto = (p > 0.5) == g
            k, n = int(acerto.sum()), len(acerto)
            linha[nome] = {"n": n, "acuracia": round(k / n, 4), "ic95": wilson(k, n),
                           "ece": res.get("teste", {}).get(t, {}).get("ece"),
                           "recall": res.get("teste", {}).get(t, {}).get("recall"),
                           "positivos": int(g.sum())}
        if pb is not None and pn is not None and len(pb) == len(pn) and (gb == gn).all():
            ab, an = (pb > 0.5) == gb, (pn > 0.5) == gn
            b, c = int((ab & ~an).sum()), int((~ab & an).sum())
            linha["pareado"] = {"so_v3_acerta": b, "so_v6_acerta": c, "mcnemar_p": mcnemar_exato(b, c),
                                "delta_pp": round((an.mean() - ab.mean()) * 100, 2)}
        out[t] = linha
    return out


def auc(neg, pos) -> float:
    """Mann-Whitney: P(página com injeção pontua acima da benigna), empates contam meio."""
    neg, pos = np.asarray(neg), np.asarray(pos)
    maior = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return round(float(maior / (len(neg) * len(pos))), 4)


NEGATIVOS = {"tecnico": ("so_perguntas", "so_respostas", "docstrings"), "assistente": ("massive_pt", "dolly-pt", "dolly")}
POSITIVOS = {"weni": ("weni",), "xtram1-pt": ("xtram1-pt",)}


def troca(modelos: str) -> dict:
    """Detecção x aviso falso independente do limiar: AUC e recall no limiar que segura o aviso falso em 2% e 5%.

    Positivos e negativos vêm de testes diferentes (os mesmos itens para v3 e v6); só itens com o rótulo certo."""
    def junta(testes, rotulo):
        xs = []
        for t in testes:
            p, g = carregar_probs(modelos, t)
            if p is not None:
                xs.append(p[g == rotulo])
        return np.concatenate(xs) if xs else None
    out = {}
    for np_nome, pos_t in POSITIVOS.items():
        pos = junta(pos_t, True)
        for nn, neg_t in NEGATIVOS.items():
            neg = junta(neg_t, False)
            if pos is None or neg is None:
                continue
            linha = {"n_pos": len(pos), "n_neg": len(neg), "auc": auc(neg, pos)}
            for alvo in (0.02, 0.05):
                lim = float(np.quantile(neg, 1 - alvo, method="higher"))
                lim = np.nextafter(lim, 2.0) if (neg >= lim).mean() > alvo else lim
                linha[f"limiar_af_{int(alvo * 100)}pct"] = round(float(lim), 6)
                linha[f"recall_af_{int(alvo * 100)}pct"] = round(float((pos >= lim).mean()), 4)
                linha[f"af_real_{int(alvo * 100)}pct"] = round(float((neg >= lim).mean()), 4)
            linha["af_no_0_5"] = round(float((neg > 0.5).mean()), 4)
            linha["recall_no_0_5"] = round(float((pos > 0.5).mean()), 4)
            out[f"{np_nome}_x_{nn}"] = linha
    return out


def paginas(arq: Path) -> dict:
    d = json.loads(arq.read_text(encoding="utf-8"))
    b, i = np.array(d["benignas"]), np.array(d["com_injecao"])
    h = len(i) // 2
    por_limiar = []
    for lim in LIMIARES:
        fp = int((b >= lim).sum())
        det = i >= lim
        por_limiar.append({"limiar": lim, "aviso_falso": round(fp / len(b), 4), "aviso_falso_ic95": wilson(fp, len(b)),
                           "deteccao": round(float(det.mean()), 4), "deteccao_ic95": wilson(int(det.sum()), len(det)),
                           "deteccao_weni": round(float(det[:h].mean()), 4),
                           "deteccao_xtram1": round(float(det[h:].mean()), 4)})
    # menor limiar que deixa o aviso falso <= 2% (critério do hook) e a detecção nele
    cands = sorted(set(np.round(b, 6).tolist() + [0.5]))
    criterio = None
    for lim in cands:
        lim_ef = np.nextafter(lim, 2.0) if lim != 0.5 else 0.5
        if (b >= lim_ef).mean() <= ALVO_AVISO_FALSO:
            criterio = {"limiar": round(float(lim_ef), 6), "aviso_falso": round(float((b >= lim_ef).mean()), 4),
                        "deteccao": round(float((i >= lim_ef).mean()), 4), "possivel": bool(lim_ef <= 1.0)}
            break
    jb = np.array(d.get("janelas_benignas", []))
    return {"arquivo": arq.name, "sonda": d.get("sonda"), "paginas": d.get("paginas"),
            "n_benignas": len(b), "n_com_injecao": len(i), "auc_pagina": auc(b, i),
            "mediana_pior_benigna": round(float(np.median(b)), 4),
            "janelas_benignas": len(jb), "janelas_benignas_acima_0_5": round(float((jb >= 0.5).mean()), 4) if len(jb) else None,
            "por_limiar": por_limiar, "criterio_aviso_falso_2pct": criterio}


def fmt_p(p) -> str:
    if p is None or p == "":
        return ""
    return "< 1e-6" if p < 1e-6 else (f"{p:.2e}" if p < 1e-3 else f"{p:.3f}").replace(".", ",")


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%".replace(".", ",")


def tabela_md(res: dict) -> str:
    L = ["# Guard v6 (correção com benignos técnicos) x v3", "",
         f"Gerado por `analysis/comparar_versoes.py` em {res['data']}. Limiar 0,5 nos testes de frase; temperatura 1.",
         "", "## Testes de frase", "",
         "| teste | o que mede | n | v3 | v6 | Δ (p.p.) | McNemar p |", "|---|---|---|---|---|---|---|"]
    for t, l in res["frases"].items():
        v3, v6, par = l.get("v3"), l.get("v6"), l.get("pareado", {})
        n = (v6 or v3 or {}).get("n", "")
        L.append(f"| {t} | {l['papel']} | {n} | {pct(v3 and v3['acuracia'])} | {pct(v6 and v6['acuracia'])} | "
                 f"{'' if not par else str(par['delta_pp']).replace('.', ',')} | {'' if not par else fmt_p(par['mcnemar_p'])} |")
    wl = res.get("weni_sem_vazamento")
    if wl:
        L += ["", "## Weni sem os itens contaminados na v3", "",
              f"{wl['contaminados']} dos {wl['contaminados'] + wl['limpos']} textos do Weni têm um vizinho (cosseno e5-base > "
              f"{str(wl['limiar_cosseno']).replace('.', ',')}) entre os exemplos que só a v3 viu no treino.", "",
              "| modelo | contaminados | limpos | IC 95% (limpos) |", "|---|---|---|---|"]
        for nome in ("v3", "v6"):
            if nome in wl:
                ic = wl[nome]["limpos_ic95"]
                L.append(f"| {nome} | {pct(wl[nome]['contaminados'])} | {pct(wl[nome]['limpos'])} | {pct(ic[0])}–{pct(ic[1])} |")
        if "pareado_limpos" in wl:
            pl = wl["pareado_limpos"]
            L.append("")
            L.append(f"Pareado nos limpos: só a v3 acerta {pl['so_v3_acerta']}, só a v6 acerta {pl['so_v6_acerta']}, McNemar p {'' if fmt_p(pl['mcnemar_p']).startswith('<') else '= '}{fmt_p(pl['mcnemar_p'])}.")
    tr = res.get("troca_deteccao_aviso_falso") or {}
    if tr.get("v3") or tr.get("v6"):
        L += ["", "## Detecção x aviso falso, sem fixar limiar (frases)", "",
              "Positivos de um teste contra negativos de outro; AUC e recall no limiar que segura o aviso falso em 2% / 5%.",
              "Probabilidades gravadas com 4 casas (empates em 0 e 1 limitam a resolução).", "",
              "| par | AUC v3 | AUC v6 | recall v3 @AF 2% | recall v6 @AF 2% | recall v3 @AF 5% | recall v6 @AF 5% | AF v3 @0,5 | AF v6 @0,5 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for par in sorted(set(tr.get("v3", {})) | set(tr.get("v6", {}))):
            a3, a6 = tr.get("v3", {}).get(par, {}), tr.get("v6", {}).get(par, {})
            L.append(f"| {par} | {a3.get('auc', '—')} | {a6.get('auc', '—')} | {pct(a3.get('recall_af_2pct'))} | "
                     f"{pct(a6.get('recall_af_2pct'))} | {pct(a3.get('recall_af_5pct'))} | {pct(a6.get('recall_af_5pct'))} | "
                     f"{pct(a3.get('af_no_0_5'))} | {pct(a6.get('af_no_0_5'))} |")
    for chave, titulo in (("paginas_640", "janela 640/160 (a do hook)"), ("paginas_1500", "janela 1500/200")):
        pag = res.get(chave) or {}
        if not pag.get("v3") and not pag.get("v6"):
            continue
        L += ["", f"## Página — {titulo}", "",
              "| limiar | aviso falso v3 | aviso falso v6 | detecção v3 | detecção v6 | det. Weni v6 | det. xTRam1 v6 |",
              "|---|---|---|---|---|---|---|"]
        a, b = pag.get("v3") or {}, pag.get("v6") or {}
        for k, lim in enumerate(LIMIARES):
            ra = (a.get("por_limiar") or [{}] * len(LIMIARES))[k]
            rb = (b.get("por_limiar") or [{}] * len(LIMIARES))[k]
            L.append(f"| {lim} | {pct(ra.get('aviso_falso'))} | {pct(rb.get('aviso_falso'))} | {pct(ra.get('deteccao'))} | "
                     f"{pct(rb.get('deteccao'))} | {pct(rb.get('deteccao_weni'))} | {pct(rb.get('deteccao_xtram1'))} |")
        def crit(c):
            if not c:
                return "—"
            if not c.get("possivel", True):
                return "inalcançável (exigiria limiar > 1)"
            return f"limiar {c['limiar']}, aviso falso {pct(c['aviso_falso'])}, detecção {pct(c['deteccao'])}"
        L += ["", f"AUC por página: v3 {a.get('auc_pagina')} · v6 {b.get('auc_pagina')}.",
              f"Menor limiar com aviso falso ≤ 2%: v3 {crit(a.get('criterio_aviso_falso_2pct'))} · "
              f"v6 {crit(b.get('criterio_aviso_falso_2pct'))}.",
              f"Janelas benignas com P ≥ 0,5: v3 {pct(a.get('janelas_benignas_acima_0_5'))} · v6 {pct(b.get('janelas_benignas_acima_0_5'))}. "
              f"Impressão das páginas: v3 {a.get('paginas')} · v6 {b.get('paginas')}."]
    return chr(10).join(L) + chr(10)


def main() -> None:
    import time
    ap = argparse.ArgumentParser()
    # pastas de probabilidades e JSONs de resultado aceitam vários valores separados por vírgula
    ap.add_argument("--base", required=True); ap.add_argument("--nova", required=True)
    ap.add_argument("--res-base", required=True); ap.add_argument("--res-nova", required=True)
    ap.add_argument("--pag-base"); ap.add_argument("--pag-nova")
    ap.add_argument("--pag1500-base"); ap.add_argument("--pag1500-nova")
    ap.add_argument("--weni-vizinhos", help="JSON {max_cos: [...]} por texto do Weni (contaminação da v3)")
    ap.add_argument("--extra", help="JSON com campos extras (treino, contagens) para o resultado")
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    rb, rn = juntar_resultados(a.res_base), juntar_resultados(a.res_nova)
    res = {"data": time.strftime("%Y-%m-%d"), "modelos": {"v3": a.base, "v6": a.nova},
           "resultados_brutos": {"v3": rb["arquivos"], "v6": rn["arquivos"]},
           "frases": frases(a.base, a.nova, rb, rn)}
    if a.weni_vizinhos:
        res["weni_sem_vazamento"] = weni_limpo(a.base, a.nova, Path(a.weni_vizinhos))
    res["troca_deteccao_aviso_falso"] = {"v3": troca(a.base), "v6": troca(a.nova)}
    for chave, pb, pn in (("paginas_640", a.pag_base, a.pag_nova), ("paginas_1500", a.pag1500_base, a.pag1500_nova)):
        res[chave] = {k: paginas(Path(p)) for k, p in (("v3", pb), ("v6", pn)) if p and Path(p).exists()}
    if a.extra:
        res["extra"] = json.loads(Path(a.extra).read_text(encoding="utf-8"))
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8",
                                          newline=chr(10))
    tabelas = saida.with_name(saida.name + "-tabelas.md")      # o texto (v6.md) embute estas tabelas
    tabelas.write_text(tabela_md(res), encoding="utf-8", newline=chr(10))
    print(saida.with_suffix(".json"), tabelas)


if __name__ == "__main__":
    main()
