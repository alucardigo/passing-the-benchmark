"""Encoder congelado que alimenta as sondas. Mesmo código no treino e no uso.

- `e5`: intfloat/multilingual-e5-base, bi-encoder treinado para similaridade (prefixo "query: "), na
  revisão fixada em ptguard/revisoes.json.

Os textos são embedados do menor para o maior: lote misturado paga padding até o maior item
(medido: mais de 25 min para ~8 mil textos curtos sem ordenar).
"""
from __future__ import annotations

from typing import Callable, List, Sequence

import numpy as np

from .config import revisao

E5_REPO = "intfloat/multilingual-e5-base"
MAX_LEN = 256
BATCH = 32

Embed = Callable[[Sequence[str]], np.ndarray]


def length_sorted(fn: Embed) -> Embed:
    def run(texts: Sequence[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return fn(texts)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = fn([texts[i] for i in order])
        restored = np.empty_like(out)
        restored[order] = out
        return restored
    return run


def e5_encoder() -> Embed:
    import torch
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(E5_REPO, revision=revisao(E5_REPO))
    model = AutoModel.from_pretrained(E5_REPO, revision=revisao(E5_REPO)).eval()

    def embed(texts: Sequence[str]) -> np.ndarray:
        parts: List[np.ndarray] = []
        with torch.inference_mode():
            for start in range(0, len(texts), BATCH):
                enc = tok(["query: " + t for t in texts[start:start + BATCH]], padding=True,
                          truncation=True, max_length=MAX_LEN, return_tensors="pt")
                hidden = model(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).float()
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1.0)
                parts.append(torch.nn.functional.normalize(pooled, dim=-1).numpy())
        return np.concatenate(parts) if parts else np.zeros((0, 768), dtype=np.float32)
    return length_sorted(embed)
