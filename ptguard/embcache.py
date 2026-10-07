"""Cache persistente de embeddings, SÓ para dado público (bases abertas de treino e avaliação).

Texto privado nunca passa por aqui: o cache grava em disco a chave e o vetor de cada texto.
Chave = sha1 do texto; vetores em <cache>/embcache/<encoder>.npz. Cada rodada de treino só embeda o
que é novo (a rodada A do guard gastou 46 min recalculando tudo).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Dict, Sequence

import numpy as np

Embed = Callable[[Sequence[str]], np.ndarray]


class CachedEmbedder:
    def __init__(self, embed: Embed, path: Path):
        self.embed, self.path = embed, Path(path)
        self.vectors: Dict[str, np.ndarray] = {}
        if self.path.exists():
            data = np.load(self.path)
            self.vectors = dict(zip(data["keys"].tolist(), data["vecs"]))

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def __call__(self, texts: Sequence[str]) -> np.ndarray:
        keys = [self.key(t) for t in texts]
        missing = {}
        for k, t in zip(keys, texts):
            if k not in self.vectors and k not in missing:
                missing[k] = t
        if missing:
            new = self.embed(list(missing.values()))
            self.vectors.update(zip(missing.keys(), new))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(self.path, keys=np.array(list(self.vectors)), vecs=np.stack(list(self.vectors.values())))
        return np.stack([self.vectors[k] for k in keys])
