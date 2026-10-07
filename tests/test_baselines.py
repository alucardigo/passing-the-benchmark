"""Métricas da comparação de guards públicos (bench/baselines.py): sem modelo, só a conta."""
import numpy as np

from conftest import carregar_script

gb = carregar_script("bench/baselines.py", "baselines")


def test_auroc_counts_ties_as_half():
    assert gb.auroc([0.0, 1.0], [2.0, 3.0]) == 1.0
    assert gb.auroc([5.0], [5.0]) == 0.5
    assert gb.auroc([1.0, 3.0], [2.0]) == 0.5


def test_rate_thresholds_probability_from_log_odds():
    lo = np.array([0.0, 2.2, 10.0, -3.0])          # P = 0,5 · 0,90 · ~1 · 0,05
    assert gb.taxa(lo, 0.5) == 0.75
    assert gb.taxa(lo, 0.9) == 0.5
    assert gb.taxa(lo, 0.999) == 0.25


def test_operating_point_keeps_false_alarm_at_or_below_target():
    benignas = np.arange(100, dtype=float)          # 2% de 100 = 2 páginas acima do corte
    com_inj = np.array([97.5, 98.5, 150.0, 10.0])
    op = gb.ponto_de_operacao(benignas, com_inj, alvo=0.02)
    assert op["corte_log_odds"] == 97.0
    assert op["aviso_falso"] == 0.02
    assert op["deteccao"] == 0.75


def test_saturated_probability_is_written_as_one_minus_epsilon():
    assert gb.corte_p({"corte_1_menos_p": 3.2e-05}) == "1−3e-5"
    assert gb.corte_p({"corte_1_menos_p": 0.25}) == "0,750"


def test_windows_remember_their_page():
    textos, dono = gb.janelas_de([{"texto": "a" * 1000}, {"texto": "b" * 100}], 640, 160)
    assert dono.tolist() == [0, 0, 0, 1]
    pior, onde = gb.pior_por_pagina(np.array([-2.0, 5.0, 1.0, -7.0]), dono, 2)
    assert pior.tolist() == [5.0, -7.0] and onde.tolist() == [1, 3]


def test_page_report_has_no_third_party_text_unless_asked():
    class Falso:
        max_length = 256

        def log_odds(self, textos):
            return np.array([float(len(t) % 7) for t in textos])

        def n_tokens(self, textos):
            return np.array([len(t) // 3 for t in textos])
    paginas = {"benignas": [{"pacote": f"p{i}", "texto": "x" * (700 + 50 * i)} for i in range(6)],
               "com_injecao": [{"pacote": "p0", "fonte": "weni", "texto": "y" * 900},
                               {"pacote": "p1", "fonte": "xtram1", "texto": "z" * 800}]}
    sem = gb.avaliar_paginas(Falso(), paginas, 640, 160)
    assert all("trecho" not in b and "janela" in b for b in sem["benignas_mais_suspeitas"])
    com = gb.avaliar_paginas(Falso(), paginas, 640, 160, trechos=True)
    assert all("trecho" in b for b in com["benignas_mais_suspeitas"])
