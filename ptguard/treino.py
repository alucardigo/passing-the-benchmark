"""Treino de sondas: regressão logística calibrada sobre embedding congelado.

Regra de protocolo (vale para quem chama): C, peso de classe e temperatura escolhidos SÓ na validação;
o teste só mede. A sonda salva em <modelos>/<nome>.npz é lida por `ptguard.sonda`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np

from .config import MODELOS


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def calibrated(probs: np.ndarray, t: float) -> np.ndarray:
    return softmax(np.log(np.clip(probs, 1e-12, 1.0)) / t)


def fit_temperature(probs: np.ndarray, gold_idx: np.ndarray) -> float:
    """Temperatura que minimiza a log-loss na validação (grade log). Não muda o argmax."""
    logp = np.log(np.clip(probs, 1e-12, 1.0))
    best_t, best_nll = 1.0, np.inf
    for t in np.logspace(-1, 1.3, 60):
        scaled = softmax(logp / t)
        nll = -np.mean(np.log(np.clip(scaled[np.arange(len(gold_idx)), gold_idx], 1e-12, 1.0)))
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def fit_probe(xtr, ytr, xdev, ydev, cs: Sequence[float] = (0.05, 0.2, 1.0, 4.0)):
    """(score, C, class_weight, modelo) com a melhor acurácia balanceada na validação."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    best = None
    for weight in (None, "balanced"):
        for c in cs:
            model = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=3000, class_weight=weight))
            model.fit(xtr, ytr)
            pred = model.predict(xdev)
            score = float(np.mean([np.mean(pred[ydev == k] == k) for k in np.unique(ydev)]))
            if best is None or score > best[0]:
                best = (score, c, weight, model)
    return best


def save_probe(model, name: str, encoder: str, temperature: float, metrics: Dict,
               pasta: Optional[Path] = None) -> Path:
    scaler, lr = model.named_steps["standardscaler"], model.named_steps["logisticregression"]
    pasta = Path(pasta or MODELOS)
    pasta.mkdir(parents=True, exist_ok=True)
    out = pasta / f"{name}.npz"
    np.savez(out, mean=scaler.mean_, scale=scaler.scale_, coef=lr.coef_, intercept=lr.intercept_,
             classes=np.array([str(c) for c in lr.classes_]), temperature=np.array(temperature))
    meta = {"sonda": name, "encoder": encoder, "temperatura": temperature, "teste": metrics,
            "treinado_em": time.strftime("%Y-%m-%d")}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
