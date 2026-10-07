"""Métricas de avaliação de um classificador contra rótulos reais. Python puro, sem numpy.

O que importa para decidir se um classificador serve:
- acurácia contra a base majoritária (acertar 60% quando 55% é uma classe só não é mérito);
- ECE: quanto a confiança mente. Os checkpoints saem de fábrica confiantes demais;
- cobertura × acurácia por limiar: é isso que diz qual confiança mínima exigir;
- nota corrigida pelo acaso (Decision Index): 0 = chute uniforme, 100 = perfeito; pergunta sem
  resposta conta como erro, e a fração respondida aparece separada.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence

DEFAULT_THRESHOLDS = (0.5, 0.7, 0.8, 0.9, 0.95, 0.99)


def ece(confs: Sequence[float], hits: Sequence[bool], bins: int = 10) -> float:
    """Expected Calibration Error: média ponderada de |acerto - confiança| por faixa."""
    total = len(confs)
    if total == 0:
        return 0.0
    buckets: Dict[int, List[int]] = {}
    for i, c in enumerate(confs):
        buckets.setdefault(min(int(c * bins), bins - 1), []).append(i)
    err = 0.0
    for idx in buckets.values():
        acc = sum(hits[i] for i in idx) / len(idx)
        mean_conf = sum(confs[i] for i in idx) / len(idx)
        err += len(idx) / total * abs(acc - mean_conf)
    return err


def coverage_table(confs: Sequence[float], hits: Sequence[bool],
                   thresholds: Sequence[float] = DEFAULT_THRESHOLDS) -> List[Dict]:
    """Para cada limiar: fração decidida sem escalar (confiança >= limiar) e a acurácia dessa fração."""
    rows = []
    for t in thresholds:
        kept = [h for c, h in zip(confs, hits) if c >= t]
        rows.append({
            "limiar": t,
            "cobertura": len(kept) / len(confs) if confs else 0.0,
            "acuracia": sum(kept) / len(kept) if kept else None,
            "n": len(kept),
        })
    return rows


def skill(raw: float, chance: float) -> float:
    """Nota do Decision Index: (acerto - acaso) / (1 - acaso), em 0..100 (negativa = pior que chutar)."""
    return (raw - chance) / (1 - chance) * 100 if chance < 1 else 0.0


def majority_baseline(gold: Sequence[str]) -> Dict:
    label, count = Counter(gold).most_common(1)[0]
    return {"rotulo": label, "acuracia": count / len(gold)}


def evaluate_choice(gold: Sequence[str], pred: Sequence[Optional[str]], confs: Sequence[float],
                    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
                    top_confusions: int = 8, n_opcoes: Optional[int] = None) -> Dict:
    """`pred` None = sem resposta (erro do motor, timeout): conta como erro. `n_opcoes` define o acaso
    (1/n); sem ele, usa as classes vistas no ouro."""
    hits = [p is not None and g == p for g, p in zip(gold, pred)]
    recall: Dict[str, Optional[float]] = {}
    for label in sorted(set(gold)):
        idx = [i for i, g in enumerate(gold) if g == label]
        recall[label] = round(sum(hits[i] for i in idx) / len(idx), 4)
    confusions = Counter((g, p) for g, p in zip(gold, pred) if g != p)
    acuracia = sum(hits) / len(hits)
    chance = 1 / (n_opcoes or len(set(gold)))
    return {
        "n": len(gold),
        "acuracia": round(acuracia, 4),
        "acuracia_balanceada": round(sum(recall.values()) / len(recall), 4),
        "nota": round(skill(acuracia, chance), 1),
        "respondidos": round(sum(p is not None for p in pred) / len(pred), 4),
        "base_majoritaria": majority_baseline(gold),
        "ece": round(ece(confs, hits), 4),
        "recall": recall,
        "cobertura": coverage_table(confs, hits, thresholds),
        "confusoes": [{"real": g, "previsto": p, "n": n}
                      for (g, p), n in confusions.most_common(top_confusions)],
    }


def wilson(k: int, n: int, z: float = 1.96) -> List[Optional[float]]:
    """Intervalo de Wilson (95% por padrão) para k sucessos em n; [None, None] sem dados."""
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / den
    return [round(max(0.0, centro - meia), 4), round(min(1.0, centro + meia), 4)]
