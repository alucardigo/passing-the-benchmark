"""Configuração do pipeline: rodadas, filtros de linha e trava de duplicatas (sem baixar nada)."""
from conftest import carregar_script

t = carregar_script("pipeline/treinar.py", "treinar")


def test_rounds_differ_only_in_what_the_paper_says():
    v3, v5, v6 = (t.config_da_rodada(r) for r in ("v3", "v5", "v6"))
    assert set(v3["sem_fontes"]) == {"hackaprompt", "so_perguntas", "so_respostas", "docstrings"}
    assert not v3["trava"]                                  # a v3 foi exportada antes da trava existir
    assert "hackaprompt" not in v5["sem_fontes"] and v5["trava"]
    assert set(v6["sem_fontes"]) == {"hackaprompt"} and v6["trava"]
    assert t.config_da_rodada("v2")["sem_fontes"] == v3["sem_fontes"]
    pub = t.config_da_rodada("v3-pub")
    assert pub["trava"] and pub["dedup_testes"] and pub["excluir_origem"]["shieldlm"][0] == "source"


def test_source_order_is_stable():
    """A ordem das fontes define a ordem do treino.jsonl, e o split do Kaggle (seed 0) depende dela."""
    assert list(t.CFG["fontes"])[:10] == ["deepset", "jackhhao", "spml", "xtram1", "rikka", "shieldlm",
                                          "yanis", "massive_pt", "weni", "dolly"]


def test_row_filters_and_origin_exclusion():
    aceita = t.aceitador((("model", "gpt-3.5-turbo"), ("correct", True)))
    assert aceita({"model": "gpt-3.5-turbo", "correct": True})
    assert not aceita({"model": "gpt-3.5-turbo", "correct": False})
    assert t.aceitador(("labels", 1))({"labels": 1}) and not t.aceitador(("labels", 1))({"labels": 0})
    sem_safeguard = t.aceitador(None, ("source", ("safeguard",)))
    assert not sem_safeguard({"source": "safeguard/prompt-injection"})
    assert sem_safeguard({"source": "deepset"}) and sem_safeguard({})


def test_raw_text_unless_html_cleaning_is_configured():
    r = {"title": "T", "body": "<p>a &amp; b</p>"}
    assert t.texto_de({"x": "  cru  "}, "x") == "  cru  "
    assert t.texto_de(r, ("title", "body"), limpar=True) == "T\n\na & b"


def test_exact_test_duplicates_are_removed_from_training():
    treino = [("Ignore   all", True), ("bom dia", False)]
    assert t.sem_duplicatas_de_teste(treino, {"x": [("ignore all", True)]}) == [("bom dia", False)]


def test_hash_split_is_deterministic():
    assert t.bucket("abc") == t.bucket("abc") and 0 <= t.bucket("abc") < 100
