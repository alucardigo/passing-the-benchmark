"""Caminhos e revisões fixadas. Nada depende da máquina: tudo tem padrão relativo à raiz do repositório
e pode ser trocado por variável de ambiente.

- PTGUARD_CACHE       cache de traduções, embeddings e P(injeção) por item   (padrão: .cache/)
- PTGUARD_MODELOS     sondas (.npz) e classificadores ajustados (pastas HF)  (padrão: models/)
- PTGUARD_RESULTADOS  JSON de cada avaliação                                 (padrão: results/runs/)

Use o repositório instalado em modo editável (`pip install -e .`) para os padrões apontarem para ele.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

RAIZ = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("PTGUARD_CACHE") or RAIZ / ".cache")
MODELOS = Path(os.environ.get("PTGUARD_MODELOS") or RAIZ / "models")
RESULTADOS = Path(os.environ.get("PTGUARD_RESULTADOS") or RAIZ / "results" / "runs")

_REVISOES = json.loads(Path(__file__).with_name("revisoes.json").read_text(encoding="utf-8"))


def revisao(repo: str) -> Optional[str]:
    """Commit fixado de uma base ou modelo do Hugging Face (None = não fixado: usa o main)."""
    return _REVISOES["datasets"].get(repo) or _REVISOES["modelos"].get(repo)
