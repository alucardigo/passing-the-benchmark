"""Construtor do benchmark por página: leitura do METADATA, inserção determinística e o manifesto."""
import json

from conftest import RAIZ, carregar_script

c = carregar_script("bench/paginas/construir.py", "construir")
MANIFESTO = RAIZ / "bench" / "paginas" / "manifesto.jsonl"


def test_metadata_body_uses_universal_newlines_like_read_text():
    bruto = b"Metadata-Version: 2.1\r\nName: pacote\r\n\r\nLinha 1\r\nLinha 2\rLinha 3\r\n"
    assert c.corpo_do_metadata(bruto) == "Linha 1\nLinha 2\nLinha 3\n"


def test_metadata_body_replaces_invalid_utf8():
    assert c.corpo_do_metadata(b"Name: x\n\ncaf\xe9") == "caf�"


def test_insertion_lands_on_a_paragraph_break_and_is_deterministic():
    pagina = "a" * 100 + "\n\n" + "b" * 100 + "\n\n" + "c" * 100
    final = c.inserir(pagina, "ATAQUE", 6000)
    assert final == c.inserir(pagina, "ATAQUE", 6000)
    assert "\n\n\n\nATAQUE\n\n" in final or "\n\nATAQUE\n\n\n\n" in final
    assert final.replace("\n\nATAQUE\n\n", "", 1) == pagina


def test_insertion_respects_the_page_limit():
    assert len(c.inserir("x" * 6000, "ATAQUE", 6000)) == 6000


def test_manifest_is_consistent():
    linhas = [json.loads(x) for x in MANIFESTO.read_text(encoding="utf-8").splitlines() if x.strip()]
    cab, benignas, injecoes = c.ler_manifesto(MANIFESTO)
    assert len(linhas) == 1 + 217 + 60
    assert [b["id"] for b in benignas] == list(range(217))
    assert [i["id"] for i in injecoes] == list(range(60))
    assert cab["impressao_benignas"] == "349cf30a6cebfa99"
    assert {b["origem"] for b in benignas} == {"pep658", "sdist-pkg-info"}
    assert sum(b["origem"] == "pep658" for b in benignas) == 216
    assert all(len(b["sha256_pagina"]) == 64 and 1500 < b["chars"] <= 6000 for b in benignas)
    assert [i["fonte"] for i in injecoes] == ["weni"] * 30 + ["xtram1"] * 30
    assert all(i["pagina_hospedeira"] == i["id"] for i in injecoes)
    assert set(cab["fontes_ataque"]) == {"weni", "xtram1"}
    # nenhum texto de terceiro no manifesto: só campos de identificação e hash
    permitidos = {"tipo", "id", "pacote", "versao", "origem", "arquivo", "sha256_metadata", "sha256_arquivo",
                  "fim_de_linha_unico", "sha256_pagina", "chars", "fonte", "posicao_md5", "md5_ataque",
                  "pagina_hospedeira", "sha256_pagina_final"}
    assert all(set(x) <= permitidos for x in benignas + injecoes)


class BaixadorFalso:
    """Serve um METADATA fixo como se viesse do PyPI."""
    def __init__(self, bruto):
        self.bruto = bruto

    def indice(self, pacote):
        return {"files": [{"filename": "p-1.0-py3-none-any.whl", "url": "https://exemplo/p.whl"}]}

    def conteudo(self, url, sha):
        return self.bruto


def test_benign_page_is_checked_against_both_hashes():
    bruto = b"Name: p\r\n\r\ncorpo da pagina\r\n"
    item = {"pacote": "p", "arquivo": "p-1.0-py3-none-any.whl", "origem": "pep658",
            "sha256_metadata": c.sha256(bruto), "sha256_pagina": c.sha256("corpo da pagina\n")}
    assert c.pagina_benigna(item, BaixadorFalso(bruto), 6000) == "corpo da pagina\n"
    ruim = {**item, "sha256_pagina": "0" * 64}
    try:
        c.pagina_benigna(ruim, BaixadorFalso(bruto), 6000)
    except ValueError as exc:
        assert "página" in str(exc)
    else:
        raise AssertionError("deveria recusar página com hash diferente")


def test_trailing_blank_lines_collapse_only_when_the_manifest_says_so():
    bruto = b"Name: p\n\ncorpo\n\n\n"
    base = {"pacote": "p", "arquivo": "p-1.0-py3-none-any.whl", "origem": "pep658", "sha256_metadata": c.sha256(bruto)}
    assert c.pagina_benigna({**base, "sha256_pagina": c.sha256("corpo\n\n\n")}, BaixadorFalso(bruto), 6000) == "corpo\n\n\n"
    item = {**base, "fim_de_linha_unico": True, "sha256_pagina": c.sha256("corpo\n")}
    assert c.pagina_benigna(item, BaixadorFalso(bruto), 6000) == "corpo\n"
