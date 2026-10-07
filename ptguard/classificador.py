"""Classificador ajustado: pasta Hugging Face (sequence classification), como o e5-large v3/v6.

É o e5 ajustado no Kaggle (kaggle/gerar_notebook.py). Responde no MESMO formato da sonda. Prefixo e
temperatura vêm do arquivo de metadados da pasta (`ptguard.json`; o nome antigo `laya-classificador.json`
também é lido). Sem esse arquivo, o padrão do estudo: prefixo "query: " e temperatura 1,0 (logits crus;
nenhuma versão ajustada teve calibração de temperatura).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

import numpy as np

Forward = Callable[[Sequence[str]], np.ndarray]   # textos -> logits [n, classes]

META_NOMES = ("ptguard.json", "laya-classificador.json")
META_PADRAO = {"temperatura": 1.0, "prefixo": "query: "}
MAX_LENGTH = 256


def ler_meta(path: Path) -> Dict[str, Any]:
    """Metadados (prefixo, temperatura) de uma pasta de classificador; o padrão do estudo se não houver."""
    for nome in META_NOMES:
        arq = Path(path) / nome
        if arq.exists():
            return {**META_PADRAO, **json.loads(arq.read_text(encoding="utf-8"))}
    return dict(META_PADRAO)


@dataclass(frozen=True)
class Classificador:
    name: str
    labels: List[str]
    temperature: float
    forward: Forward

    @classmethod
    def load(cls, path: Path) -> "Classificador":
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path, dtype=torch.float32).eval()
        meta = ler_meta(path)

        def forward(texts: Sequence[str]) -> np.ndarray:
            with torch.inference_mode():
                enc = tok([meta["prefixo"] + t for t in texts], padding=True,
                          truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
                return model(**enc).logits.float().numpy()
        labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
        return cls(name=Path(path).name, labels=labels, temperature=float(meta["temperatura"]), forward=forward)

    def logits(self, texts: Sequence[str], batch: int = 32) -> np.ndarray:
        """Do menor para o maior texto, em lotes: lote misturado paga padding até o maior (medido: ~3x)."""
        texts = list(texts)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), len(self.labels)), dtype=np.float64)
        for start in range(0, len(order), batch):
            idx = order[start:start + batch]
            out[idx] = np.asarray(self.forward([texts[i] for i in idx]), dtype=np.float64)
        return out

    def answers(self, texts: Sequence[str]) -> List[Dict[str, Any]]:
        z = self.logits(texts) / self.temperature
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        binary = sorted(self.labels) == ["false", "true"]     # guard: pergunta sim/não
        out = []
        for row in p:
            probs = {c: round(float(v), 4) for c, v in zip(self.labels, row)}
            top = max(probs, key=probs.get)
            if binary:
                out.append({"type": "noul", "noul": probs["true"], "probabilities": probs,
                            "answer_confidence": probs[top], "fonte": f"classificador:{self.name}"})
            else:
                out.append({"type": "choice", "choice": top, "probabilities": probs,
                            "answer_confidence": probs[top], "fonte": f"classificador:{self.name}"})
        return out

    def p_injecao(self, texts: Sequence[str]) -> List[float]:
        """P(injeção) por texto (classe "true"), com 4 casas, como todas as avaliações do estudo."""
        return [float(a["probabilities"]["true"]) for a in self.answers(texts)]


def is_classificador(path: Path) -> bool:
    """Pasta com pesos de sequence classification (config.json + pesos)."""
    p = Path(path)
    return (p / "config.json").exists() and (any(p.glob("*.safetensors")) or (p / "pytorch_model.bin").exists())
