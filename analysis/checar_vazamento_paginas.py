"""Confere que o treino exportado não contém as páginas do teste por página (descrições de pacotes).

    python analysis/checar_vazamento_paginas.py work/v6/treino.jsonl [--base-antiga work/v3/treino.jsonl]
                                                [--paginas work/paginas.json]

Três testes, do mais estrito ao mais frouxo, contra as 217 páginas benignas que bench/paginas/construir.py
remonta: (1) texto de treino idêntico a uma página; (2) texto de treino (>= 200 chars) contido numa página
ou página contida no texto; (3) 13-gramas de palavras em comum (o critério de contaminação usado em
avaliações de LLM). Só conta e mostra os 13-gramas mais frequentes, para separar boilerplate (licença,
badge) de cópia de página. Com --base-antiga, mede também quanto do treino da v3 está no da v6 (a v6 deve
ser a v3 + benignos técnicos).

No estudo, a mesma conferência rodou contra os 329 METADATA de todos os ambientes locais (um
superconjunto das 217 páginas): nenhum texto idêntico, nenhum trecho de 200+ caracteres em comum, e 9
textos com algum 13-grama, todos boilerplate XML/XHTML.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
N = 13


def metadados(paginas: Path) -> dict:
    """pacote -> página benigna, do benchmark remontado (bench/paginas/construir.py)."""
    d = json.loads(Path(paginas).read_text(encoding="utf-8"))
    return {p["pacote"]: p["texto"] for p in d["benignas"]}


def palavras(t: str) -> list:
    return re.findall(r"\w+", t.lower())


def ngramas(t: str) -> set:
    w = palavras(t)
    return {" ".join(w[i:i + N]) for i in range(len(w) - N + 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("treino")
    ap.add_argument("--base-antiga")
    ap.add_argument("--paginas", default=str(RAIZ / "work" / "paginas.json"))
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.treino).open(encoding="utf-8")]
    textos = [r["texto"] for r in rows]
    meta = metadados(Path(a.paginas))
    corpos = list(meta.values())
    juntos = chr(30).join(corpos)
    exatos = sum(1 for t in textos if t in set(corpos))
    contidos = sum(1 for t in textos if len(t) >= 200 and t in juntos)
    readme_no_treino = sum(1 for c in corpos if len(c) >= 200 and any(c in t for t in textos if len(t) >= len(c)))
    idx = collections.defaultdict(set)
    for k, c in enumerate(corpos):
        for g in ngramas(c):
            idx[g].add(k)
    comuns = collections.Counter()
    textos_com = 0
    readmes_tocados = set()
    for t in textos:
        gs = [g for g in ngramas(t) if g in idx]
        if gs:
            textos_com += 1
            comuns.update(set(gs))
            for g in gs:
                readmes_tocados |= idx[g]
    res = {"treino": Path(a.treino).as_posix(), "n_treino": len(textos), "n_metadata": len(corpos),
           "identicos_a_readme": exatos, "treino_contido_em_readme_200c": contidos,
           "readme_contido_no_treino": readme_no_treino, f"textos_com_{N}grama_de_readme": textos_com,
           "readmes_com_algum_13grama_no_treino": len(readmes_tocados),
           "rotulos": dict(collections.Counter(r["rotulo"] for r in rows)),
           f"{N}gramas_mais_comuns": [[g, n] for g, n in comuns.most_common(8)]}
    if a.base_antiga:
        antigos = [json.loads(l)["texto"] for l in Path(a.base_antiga).open(encoding="utf-8")]
        novos = set(textos)
        res["v3_no_v6"] = {"n_v3": len(antigos), "presentes": sum(t in novos for t in antigos),
                           "presentes_sem_espacos": len({t.strip() for t in antigos} & {t.strip() for t in textos})}
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    main()
