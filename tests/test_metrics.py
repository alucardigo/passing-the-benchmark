"""Métricas da avaliação."""
import pytest

from ptguard.metrics import coverage_table, ece, evaluate_choice, majority_baseline


def test_ece_is_zero_when_confidence_matches_hit_rate():
    # 10 respostas a 0.8, 8 certas: confiança diz exatamente a taxa de acerto.
    confs = [0.8] * 10
    hits = [True] * 8 + [False] * 2
    assert ece(confs, hits) == pytest.approx(0.0)


def test_ece_measures_overconfidence():
    # O checkpoint multilíngue devolve p=1.00 e erra metade: ECE 0.5.
    assert ece([1.0] * 4, [True, False, True, False]) == pytest.approx(0.5)


def test_coverage_table_reports_accuracy_among_kept_answers():
    rows = coverage_table([0.95, 0.9, 0.6, 0.4], [True, True, False, False], thresholds=[0.5, 0.9])
    assert rows == [
        {"limiar": 0.5, "cobertura": 0.75, "acuracia": pytest.approx(2 / 3), "n": 3},
        {"limiar": 0.9, "cobertura": 0.5, "acuracia": 1.0, "n": 2},
    ]


def test_coverage_table_with_nothing_kept_has_no_accuracy():
    rows = coverage_table([0.2], [True], thresholds=[0.9])
    assert rows[0]["acuracia"] is None and rows[0]["n"] == 0


def test_majority_baseline_is_the_share_of_the_most_common_label():
    assert majority_baseline(["a", "a", "b", "c"]) == {"rotulo": "a", "acuracia": 0.5}


def test_evaluate_choice_summarises_accuracy_recall_and_confusions():
    gold = ["benigno", "benigno", "injecao", "injecao"]
    pred = ["benigno", "injecao", "injecao", "injecao"]
    confs = [0.9, 0.9, 0.8, 0.7]
    out = evaluate_choice(gold, pred, confs, thresholds=[0.85])
    assert out["n"] == 4
    assert out["acuracia"] == 0.75
    assert out["recall"] == {"benigno": 0.5, "injecao": 1.0}
    assert out["confusoes"] == [{"real": "benigno", "previsto": "injecao", "n": 1}]
    assert out["base_majoritaria"]["acuracia"] == 0.5


def test_skill_is_chance_corrected_like_decision_index():
    from ptguard.metrics import skill
    assert skill(0.25, chance=0.25) == 0.0          # chute uniforme em 4 opções
    assert skill(1.0, chance=0.25) == 100.0
    assert round(skill(0.625, chance=0.25), 1) == 50.0


def test_unanswered_counts_as_wrong_and_is_reported():
    from ptguard.metrics import evaluate_choice
    r = evaluate_choice(["a", "b", "a", "b"], ["a", None, "a", "a"], [0.9, 0.0, 0.8, 0.6], n_opcoes=2)
    assert r["respondidos"] == 0.75
    assert r["acuracia"] == 0.5                      # o sem resposta conta como erro
    assert r["nota"] == 0.0                          # 50% com 2 opções = acaso


def test_balanced_accuracy_is_mean_recall():
    from ptguard.metrics import evaluate_choice
    r = evaluate_choice(["a", "a", "a", "b"], ["a", "a", "a", "a"], [0.9] * 4)
    assert r["acuracia"] == 0.75 and r["acuracia_balanceada"] == 0.5


def test_wilson_interval_matches_the_paper():
    from ptguard.metrics import wilson
    assert wilson(284, 300) == [0.9151, 0.9669]       # v3 no Weni: 94,7% [91,5; 96,7]
    assert wilson(217, 217)[0] == 0.9826               # aviso falso da v3 em página: [98,3; 100]
    assert wilson(0, 0) == [None, None]
