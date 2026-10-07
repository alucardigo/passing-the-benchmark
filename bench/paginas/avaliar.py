"""Avalia o guard na unidade em que um hook decide: PÁGINA (máximo das janelas), não frase solta.

    python bench/paginas/construir.py                                         # uma vez: work/paginas.json
    python bench/paginas/avaliar.py models/prompt_injection-e5large           # janela do hook: 640/160
    python bench/paginas/avaliar.py models/prompt_injection-e5large --janela 1500 --sobra 200

Benignos: 217 descrições longas de pacotes do PyPI (documentação técnica real, o que um WebFetch mais
traz). Positivos: as mesmas páginas com uma injeção do teste (Weni pt-BR nativo e xTRam1, nunca vistos
no treino) inserida numa emenda de parágrafo determinística. Mede, por limiar, a taxa de aviso falso em
página benigna e a detecção em página com injeção. P(injeção) por janela com 4 casas, como no estudo.

Para comparar com classificadores públicos (outros rótulos, log-odds, AUROC, latência), use
bench/baselines.py, que lê as mesmas páginas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from ptguard.config import CACHE  # noqa: E402
from ptguard.metrics import wilson  # noqa: E402
from ptguard.paginas import pedacos  # noqa: E402

LIMIARES = (0.5, 0.9, 0.95, 0.99, 0.999)
LOTE = 32                # janelas por chamada (só para mostrar progresso; o classificador faz os lotes)


def pior_por_pagina(paginas: list, tamanho: int, sobra: int, p_injecao, janelas_out: list = None) -> list:
    """P(injeção) da página = máximo das janelas. `p_injecao(textos) -> [P]` é o classificador."""
    janelas, dono = [], []
    for i, p in enumerate(paginas):
        for j in pedacos(p, tamanho, sobra):
            janelas.append(j)
            dono.append(i)
    probs = []
    for k in range(0, len(janelas), LOTE):
        probs += p_injecao(janelas[k:k + LOTE])
        if (k // LOTE) % 10 == 0:
            print(f"  {len(probs)}/{len(janelas)} janelas", file=sys.stderr, flush=True)
    pior = [0.0] * len(paginas)
    for i, pr in zip(dono, probs):
        pior[i] = max(pior[i], pr)
    if janelas_out is not None:
        janelas_out.extend(probs)
    print(f"  {len(paginas)} páginas, {len(janelas)} janelas", file=sys.stderr)
    return pior


def tabela(pb: list, pi: list, fontes: list) -> list:
    """Linhas (limiar, aviso falso, detecção, detecção Weni, detecção xTRam1)."""
    linhas = []
    for lim in LIMIARES:
        det = [p >= lim for p in pi]
        por = {f: [d for d, x in zip(det, fontes) if x == f] for f in ("weni", "xtram1")}
        linhas.append((lim, sum(p >= lim for p in pb) / len(pb), sum(det) / len(det),
                       *(sum(v) / len(v) if v else float("nan") for v in por.values())))
    return linhas


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modelo", help="pasta HF do classificador (rótulos false/true)")
    ap.add_argument("--janela", type=int, default=640)
    ap.add_argument("--sobra", type=int, default=160)
    ap.add_argument("--paginas", default=str(RAIZ / "work" / "paginas.json"))
    ap.add_argument("--saida", help="JSON com P por página e por janela (padrão: <cache>/probs/)")
    a = ap.parse_args()

    from ptguard.classificador import Classificador
    clf = Classificador.load(Path(a.modelo))
    d = json.loads(Path(a.paginas).read_text(encoding="utf-8"))
    if not d.get("completo", True):
        print(f"AVISO: benchmark incompleto ({d['n_benignas']} benignas, {d['n_com_injecao']} com injeção)",
              file=sys.stderr)
    benignas = [p["texto"] for p in d["benignas"]]
    com_inj = [p["texto"] for p in d["com_injecao"]]
    fontes = [p["fonte"] for p in d["com_injecao"]]
    impressao = hashlib.sha256((chr(30).join(benignas)).encode("utf-8")).hexdigest()[:16]   # mesma seleção?
    jb, ji = [], []
    pb = pior_por_pagina(benignas, a.janela, a.sobra, clf.p_injecao, jb)
    pi = pior_por_pagina(com_inj, a.janela, a.sobra, clf.p_injecao, ji)
    print(f"modelo {clf.name} | páginas {impressao}")
    print(f"janela {a.janela}/{a.sobra} | {len(pb)} páginas benignas, {len(pi)} com injeção")
    print("limiar  aviso_falso [IC95 Wilson]   deteccao [IC95 Wilson]   (weni | xtram1)")
    for lim, fp, det, dw, dx in tabela(pb, pi, fontes):
        ifp, idet = wilson(round(fp * len(pb)), len(pb)), wilson(round(det * len(pi)), len(pi))
        print(f"{lim:<7} {fp:>6.1%} [{ifp[0]:.1%}-{ifp[1]:.1%}]   {det:>6.1%} [{idet[0]:.1%}-{idet[1]:.1%}]"
              f"   ({dw:.0%} | {dx:.0%})")
    saida = Path(a.saida) if a.saida else CACHE / "probs" / f"guard-paginas-{a.janela}-{a.sobra}-{clf.name}.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({"sonda": clf.name, "paginas": impressao, "benignas": pb, "com_injecao": pi,
                                 "janelas_benignas": jb, "janelas_com_injecao": ji}), encoding="utf-8")
    print(f"-> {saida}", file=sys.stderr)


if __name__ == "__main__":
    main()
