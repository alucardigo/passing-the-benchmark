"""Remonta o benchmark por página a partir de fontes fixadas, sem redistribuir texto de terceiro.

    python bench/paginas/construir.py                       # -> work/paginas.json
    python bench/paginas/construir.py --saida outra.json --cache work/cache

O repositório não traz nenhuma página. `manifesto.jsonl` guarda só nome, versão, arquivo e hashes:

- 217 páginas benignas: a descrição longa (corpo do METADATA) de 217 pacotes do PyPI, cortada em 6.000
  caracteres. 216 vêm do core-metadata PEP 658 do PyPI (o METADATA servido à parte do wheel), conferido
  byte a byte pelo sha256; a que sobra (só sdist) vem do PKG-INFO do sdist, também conferido por hash.
- 60 páginas com injeção: as mesmas páginas com um ataque inserido numa emenda de parágrafo
  determinística. Os ataques vêm do Weni (pt-BR nativo) e do xTRam1 (teste), baixados da fonte na
  revisão fixada (30 + 30, os primeiros em ordem de md5 do texto).

Cada página remontada é conferida contra o sha256 do manifesto. O que não bate fica de fora e o arquivo
de saída declara o n efetivo (`completo: false`, lista `faltando`); nada é substituído em silêncio.
A saída tem o formato que bench/baselines.py e bench/paginas/avaliar.py leem. Ela fica em work/
(no .gitignore): cada página segue a licença do seu pacote e cada ataque, a da sua base.
"""
from __future__ import annotations

import argparse
import email
import hashlib
import io
import json
import re
import sys
import tarfile
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

RAIZ = Path(__file__).resolve().parents[2]
MANIFESTO = Path(__file__).with_name("manifesto.jsonl")
SAIDA = RAIZ / "work" / "paginas.json"
PYPI = "https://pypi.org"
USER_AGENT = "passing-the-benchmark/construir (+https://github.com/alucardigo/passing-the-benchmark)"


def sha256(dado) -> str:
    return hashlib.sha256(dado if isinstance(dado, bytes) else dado.encode("utf-8")).hexdigest()


def md5(texto: str) -> str:
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def corpo_do_metadata(bruto: bytes) -> str:
    """Corpo de um METADATA/PKG-INFO como a seleção original o leu: Path.read_text(encoding='utf-8',
    errors='replace') -- que traduz \\r\\n e \\r para \\n -- e depois email.message_from_string().get_payload().

    A tradução de fim de linha importa: 39 das 217 descrições têm \\r\\n no arquivo do PyPI."""
    texto = bruto.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    corpo = email.message_from_string(texto).get_payload()
    return corpo if isinstance(corpo, str) else ""


def inserir(pagina: str, injecao: str, max_chars: int) -> str:
    """Na emenda de parágrafo mais perto de uma posição pseudoaleatória (estável por página)."""
    alvo = int(hashlib.md5(pagina.encode("utf-8")).hexdigest()[:6], 16) % max(1, len(pagina))
    emendas = [i for i in range(len(pagina)) if pagina.startswith("\n\n", i)] or [alvo]
    pos = min(emendas, key=lambda i: abs(i - alvo))
    return (pagina[:pos] + "\n\n" + injecao + "\n\n" + pagina[pos:])[:max_chars]


def impressao(benignas: List[str]) -> str:
    """Impressão da seleção de páginas benignas (a mesma que avaliar.py imprime)."""
    return hashlib.sha256(chr(30).join(benignas).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- rede (com cache opcional)

class Baixador:
    def __init__(self, cache: Optional[Path] = None, tentativas: int = 4):
        self.cache = cache
        self.tentativas = tentativas

    def _get(self, url: str, aceitar: Optional[str] = None) -> bytes:
        cab = {"User-Agent": USER_AGENT}
        if aceitar:
            cab["Accept"] = aceitar
        for t in range(self.tentativas):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=60) as r:
                    return r.read()
            except Exception:
                if t == self.tentativas - 1:
                    raise
                time.sleep(2 ** t)
        raise RuntimeError("inalcançável")

    def conteudo(self, url: str, sha_esperado: str) -> bytes:
        """Arquivo imutável conferido por sha256; com cache, guarda pelo hash e não baixa de novo."""
        alvo = self.cache / sha_esperado if self.cache else None
        if alvo is not None and alvo.exists() and sha256(alvo.read_bytes()) == sha_esperado:
            return alvo.read_bytes()
        bruto = self._get(url)
        if alvo is not None and sha256(bruto) == sha_esperado:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(bruto)
        return bruto

    def indice(self, pacote: str) -> dict:
        """Índice Simple do PyPI em JSON (PEP 691): a URL do arquivo muda de CDN, o nome não."""
        nome = re.sub(r"[-_.]+", "-", pacote).lower()
        return json.loads(self._get(f"{PYPI}/simple/{nome}/", "application/vnd.pypi.simple.v1+json"))


def url_do_arquivo(baixador: Baixador, pacote: str, arquivo: str) -> str:
    for f in baixador.indice(pacote).get("files", []):
        if f["filename"] == arquivo:
            return f["url"]
    raise LookupError(f"{arquivo} não está mais no índice do PyPI")


def corpo_do_sdist(bruto: bytes) -> bytes:
    """PKG-INFO da raiz de um sdist .tar.gz (só lê esse membro; nada é extraído para o disco)."""
    with tarfile.open(fileobj=io.BytesIO(bruto), mode="r:gz") as tar:
        membros = [m for m in tar.getmembers() if m.isfile() and m.name.count("/") == 1
                   and m.name.endswith("/PKG-INFO")]
        if not membros:
            raise LookupError("sdist sem PKG-INFO na raiz")
        return tar.extractfile(membros[0]).read()


def pagina_benigna(item: dict, baixador: Baixador, max_chars: int) -> str:
    url = url_do_arquivo(baixador, item["pacote"], item["arquivo"])
    if item["origem"] == "pep658":
        bruto = baixador.conteudo(url + ".metadata", item["sha256_metadata"])
    elif item["origem"] == "sdist-pkg-info":
        bruto = corpo_do_sdist(baixador.conteudo(url, item["sha256_arquivo"]))
    else:
        raise ValueError(f"origem desconhecida: {item['origem']}")
    if sha256(bruto) != item["sha256_metadata"]:
        raise ValueError("metadata diferente do fixado")
    corpo = corpo_do_metadata(bruto)
    if item.get("fim_de_linha_unico"):
        # o METADATA instalado foi gerado localmente a partir do sdist (não existe no PyPI): o corpo dele é o
        # do PKG-INFO com as linhas em branco do fim reduzidas a uma quebra de linha (conferido pelo hash)
        corpo = corpo.rstrip("\n") + "\n"
    pagina = corpo[:max_chars]
    if sha256(pagina) != item["sha256_pagina"]:
        raise ValueError("página diferente da fixada")
    return pagina


# ---------------------------------------------------------------- ataques

def ataques_da_fonte(cfg: dict) -> List[str]:
    """Textos de ataque de uma base, na revisão fixada, em ordem de md5 (a amostra é o começo da lista)."""
    from datasets import load_dataset
    ds = load_dataset(cfg["repo"], revision=cfg["revisao"])[cfg["split"]]
    col, filtro = cfg["coluna"], cfg.get("filtro")
    textos = [str(r[col]) for r in ds if r.get(col) and (not filtro or r[filtro[0]] == filtro[1])]
    return sorted(textos, key=md5)


# ---------------------------------------------------------------- montagem

def ler_manifesto(caminho: Path):
    linhas = [json.loads(x) for x in caminho.read_text(encoding="utf-8").splitlines() if x.strip()]
    cab = next(x for x in linhas if x["tipo"] == "cabecalho")
    benignas = sorted((x for x in linhas if x["tipo"] == "benigna"), key=lambda x: x["id"])
    injecoes = sorted((x for x in linhas if x["tipo"] == "injecao"), key=lambda x: x["id"])
    return cab, benignas, injecoes


def construir(manifesto: Path, baixador: Baixador, log=print) -> dict:
    cab, itens_b, itens_i = ler_manifesto(manifesto)
    max_chars = cab["max_chars"]
    paginas: Dict[int, str] = {}
    faltando = []
    for k, item in enumerate(itens_b, 1):
        try:
            paginas[item["id"]] = pagina_benigna(item, baixador, max_chars)
        except Exception as exc:
            faltando.append({"tipo": "benigna", "id": item["id"], "pacote": item["pacote"],
                             "motivo": f"{type(exc).__name__}: {exc}"})
        if k % 25 == 0 or k == len(itens_b):
            log(f"  benignas {k}/{len(itens_b)} ({len(faltando)} faltando)")

    fontes = {nome: ataques_da_fonte(cfg) for nome, cfg in cab["fontes_ataque"].items()}
    com_inj, usados = [], []
    for item in itens_i:
        lista = fontes[item["fonte"]]
        texto = lista[item["posicao_md5"]] if item["posicao_md5"] < len(lista) else None
        host = paginas.get(item["pagina_hospedeira"])
        motivo = ("ataque não encontrado na revisão fixada" if texto is None or md5(texto) != item["md5_ataque"]
                  else "página hospedeira faltando" if host is None else None)
        if motivo is None:
            final = inserir(host, texto, max_chars)
            if sha256(final) != item["sha256_pagina_final"]:
                motivo = "página com injeção diferente da fixada"
        if motivo:
            faltando.append({"tipo": "injecao", "id": item["id"], "fonte": item["fonte"], "motivo": motivo})
            continue
        usados.append(texto)
        com_inj.append({"pacote": itens_b[item["pagina_hospedeira"]]["pacote"], "fonte": item["fonte"],
                        "injecao": texto, "texto": final})
    log(f"  com injeção {len(com_inj)}/{len(itens_i)}")

    benignas = [{"pacote": it["pacote"], "texto": paginas[it["id"]]} for it in itens_b if it["id"] in paginas]
    completo = not faltando
    res = {"criado": date.today().isoformat(), "origem": "bench/paginas/construir.py", "max_chars": max_chars,
           "md5_injecoes": hashlib.md5("\x1e".join(usados).encode("utf-8")).hexdigest(),
           "completo": completo, "n_benignas": len(benignas), "n_com_injecao": len(com_inj),
           "faltando": faltando, "benignas": benignas, "com_injecao": com_inj}
    if completo:
        imp = impressao([b["texto"] for b in benignas])
        if imp != cab["impressao_benignas"] or res["md5_injecoes"] != cab["md5_injecoes"]:
            raise SystemExit("todas as páginas bateram, mas a impressão do conjunto não: manifesto inconsistente")
        res["impressao_benignas"] = imp
    return res


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifesto", default=str(MANIFESTO))
    ap.add_argument("--saida", default=str(SAIDA))
    ap.add_argument("--cache", help="pasta para guardar os arquivos do PyPI já conferidos (opcional)")
    a = ap.parse_args()
    res = construir(Path(a.manifesto), Baixador(Path(a.cache) if a.cache else None),
                    log=lambda m: print(m, file=sys.stderr, flush=True))
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{res['n_benignas']} benignas, {res['n_com_injecao']} com injeção -> {saida}")
    if not res["completo"]:
        print(f"INCOMPLETO: {len(res['faltando'])} itens não bateram com o manifesto (ver 'faltando')",
              file=sys.stderr)
        return 1
    print(f"conferido: impressão {res['impressao_benignas']}, md5 das injeções {res['md5_injecoes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
