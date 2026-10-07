"""Sonda: regressão logística sobre o embedding de um encoder congelado (o e5-base).

Treina em segundos, roda em CPU e responde no mesmo formato do classificador ajustado
(`ptguard.classificador`): probabilidades por classe e a confiança da resposta.

Arquivo `<modelos>/<pergunta>-<encoder>.npz` (gerado por `pipeline/treinar.py sonda`): mean/scale do
StandardScaler, coef/intercept da regressão, classes, temperatura ajustada na validação. A sonda B do
artigo está em results/sonda-b/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .config import MODELOS


@dataclass(frozen=True)
class Sonda:
    name: str
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray
    classes: List[str]
    temperature: float

    @property
    def question(self) -> str:
        return self.name.rsplit("-", 1)[0]

    @property
    def encoder(self) -> str:
        return self.name.rsplit("-", 1)[1]

    @classmethod
    def load(cls, path: Path) -> "Sonda":
        data = np.load(path)
        return cls(name=Path(path).stem, mean=data["mean"], scale=data["scale"], coef=data["coef"],
                   intercept=data["intercept"], classes=[str(c) for c in data["classes"]],
                   temperature=float(data["temperature"]))

    def probabilities(self, embeddings: np.ndarray) -> np.ndarray:
        logits = ((embeddings - self.mean) / self.scale) @ self.coef.T + self.intercept
        z = logits / self.temperature
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def answers(self, embeddings: np.ndarray) -> List[Dict[str, Any]]:
        binary = sorted(self.classes) == ["false", "true"]   # sonda de pergunta sim/não
        out = []
        for row in self.probabilities(embeddings):
            probs = {c: round(float(p), 4) for c, p in zip(self.classes, row)}
            top = max(probs, key=probs.get)
            if binary:
                out.append({"type": "noul", "noul": probs["true"], "probabilities": probs,
                            "answer_confidence": probs[top], "fonte": f"sonda:{self.name}"})
            else:
                out.append({"type": "choice", "choice": top, "probabilities": probs,
                            "answer_confidence": probs[top], "fonte": f"sonda:{self.name}"})
        return out


def load_sonda(name: str, pasta: Path = None) -> Sonda:
    pasta = Path(pasta or MODELOS)
    path = pasta / f"{name}.npz"
    if not path.exists():
        available = ", ".join(p.stem for p in sorted(pasta.glob("*.npz"))) or "nenhuma"
        raise FileNotFoundError(f"sonda {name!r} não existe em {pasta}; disponíveis: {available}")
    return Sonda.load(path)
