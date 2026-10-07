"""Janelas de página: o mesmo recorte no hook, na avaliação por página e nos baselines.

A página é decidida pelo PIOR caso (máximo de P(injeção) entre as janelas), como um hook de agente
decidiria. Página enorme: olha só o começo (MAX_CHARS), onde injeção em página costuma estar.
"""
from __future__ import annotations

from typing import List

MAX_CHARS = 6000


def pedacos(texto: str, tamanho: int = 640, sobra: int = 160) -> List[str]:
    """Janelas com sobreposição (a injeção pode cair na emenda). 640 chars cabem nos 256 tokens do
    classificador: README técnico mede 3,04 chars/token (p10 2,61); com 1500 o fim da janela era cortado."""
    passo = max(1, tamanho - sobra)
    return [texto[i:i + tamanho] for i in range(0, max(len(texto), 1), passo) if texto[i:i + tamanho].strip()]
