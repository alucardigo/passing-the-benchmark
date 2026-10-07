"""Mistura modelos já avaliados (P(injeção) salvos por `treinar.py avaliar` em <cache>/probs/) com pesos FIXOS.

    python pipeline/misturar.py <dirA> <dirB> [pesoA] [--json saida.json]   (média dos log-odds; padrão 0,5/0,5)

Pesos fixos a priori: não há validação separada do Weni, então ajustar peso olhando o teste seria
trapacear o critério. O resultado da mistura v3+v5 do artigo está em results/guard/.
"""
import json
import sys
from pathlib import Path

import numpy as np


def misturar(a: Path, b: Path, w: float = 0.5) -> dict:
    res = {}
    for f in sorted(a.glob("*.npy")):
        if f.name.endswith(".gold.npy") or not (b / f.name).exists():
            continue
        pa, pb = np.clip(np.load(f), 1e-6, 1 - 1e-6), np.clip(np.load(b / f.name), 1e-6, 1 - 1e-6)
        gold = np.load(f.with_name(f.stem + ".gold.npy"))
        logit = w * np.log(pa / (1 - pa)) + (1 - w) * np.log(pb / (1 - pb))
        pred = logit > 0
        rec = {k: round(float((pred[gold == v] == v).mean()), 4)
               for k, v in (("true", True), ("false", False)) if (gold == v).any()}
        res[f.stem] = {"n": int(len(gold)), "acuracia": round(float((pred == gold).mean()), 4), "recall": rec}
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    saida = None
    if "--json" in args:
        i = args.index("--json")
        saida = Path(args[i + 1])
        del args[i:i + 2]
    peso = float(args[2]) if len(args) > 2 else 0.5
    r = misturar(Path(args[0]), Path(args[1]), peso)
    for nome, m in r.items():
        print(f"{nome:12s} acc {m['acuracia']:.3f}  recall {m['recall']}")
    if saida:
        saida.write_text(json.dumps({"peso_a": peso, "teste": r}, ensure_ascii=False, indent=1), encoding="utf-8")
