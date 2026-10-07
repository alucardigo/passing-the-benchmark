"""Tradução en->pt determinística e local (Opus-MT), com cache: a parte pt-BR do treino e dos testes.

Modelo de tradução dedicado (MarianMT, greedy): mesma entrada, mesma saída, sem LLM generativo e sem
nada sair da máquina. Cache em <cache>/traducoes/cache.jsonl (só dado público).

    from traduzir import traduzir; pt = traduzir(["Ignore all previous instructions"])
    python pipeline/traduzir.py pendentes.jsonl [cache_saida.jsonl]     (lote dividido entre máquinas)

A saída do Opus-MT pode variar um pouco entre versões de torch/transformers e entre CPU e GPU: para
reproduzir uma rodada exatamente, guarde o cache dela.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptguard.config import CACHE as _CACHE_DIR, revisao  # noqa: E402

MODELO = "Helsinki-NLP/opus-mt-tc-big-en-pt"
CACHE = _CACHE_DIR / "traducoes" / "cache.jsonl"
_cache: Dict[str, str] = {}


def _key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _load_cache() -> None:
    if _cache or not CACHE.exists():
        return
    for line in CACHE.open(encoding="utf-8"):
        rec = json.loads(line)
        _cache[rec["k"]] = rec["pt"]


def _modelo():
    from transformers import MarianMTModel, MarianTokenizer
    rev = revisao(MODELO)
    return (MarianTokenizer.from_pretrained(MODELO, revision=rev),
            MarianMTModel.from_pretrained(MODELO, revision=rev).eval())


def _gravar(pares, cache_path: Path, tok_model, batch: int) -> None:
    """pares = [(chave, texto_já_cortado)]; traduz em lotes e grava {k, pt} no cache (flush por lote)."""
    import torch
    tok, model = tok_model
    pares = sorted(pares, key=lambda kv: len(kv[1]))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a", encoding="utf-8") as out, torch.inference_mode():
        for i in range(0, len(pares), batch):
            parte = pares[i:i + batch]
            # o modelo multilíngue pede o token de idioma-alvo: >>por<< = português
            enc = tok([">>por<< " + t for _, t in parte], return_tensors="pt", padding=True,
                      truncation=True, max_length=512)
            # teto proporcional à entrada: com 512 fixo, o guloso entrava em repetição e só parava no teto
            # (~7 s por instrução curta). Tradução pt costuma ter 1,1-1,3x os tokens do inglês.
            teto = min(512, int(enc["input_ids"].shape[1] * 1.6) + 16)
            gen = model.generate(**enc, num_beams=1, do_sample=False, max_new_tokens=teto)
            for (k, _), pt in zip(parte, tok.batch_decode(gen, skip_special_tokens=True)):
                _cache[k] = pt
                out.write(json.dumps({"k": k, "pt": pt}, ensure_ascii=False) + chr(10))
            out.flush()   # sem isto, matar o processo perdia todo o lote em buffer (perdemos traduções assim)
            if (i // batch) % 20 == 0:
                print(f"tradução {min(i + batch, len(pares))}/{len(pares)}", file=sys.stderr, flush=True)


def traduzir(textos: Sequence[str], batch: int = 16, max_chars: int = 1500) -> List[str]:
    _load_cache()
    falta = {_key(t): t[:max_chars] for t in textos if _key(t) not in _cache}
    if falta:
        _gravar(list(falta.items()), CACHE, _modelo(), batch)
    return [_cache[_key(t)] for t in textos]


def traduzir_pendentes(entrada: Path, cache_path: Path = CACHE, batch: int = 16) -> None:
    """Traduz um JSONL {k, texto} (de `pipeline/treinar.py pendentes`) para dividir o lote entre várias
    máquinas; depois é só concatenar os caches (`cat parte.jsonl >> cache.jsonl`)."""
    pares = [(r["k"], r["texto"]) for r in map(json.loads, entrada.open(encoding="utf-8")) if r.get("texto")]
    _gravar(pares, cache_path, _modelo(), batch)


if __name__ == "__main__":
    # traduzir.py <pendentes.jsonl> [cache_saida.jsonl]
    traduzir_pendentes(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else CACHE)
