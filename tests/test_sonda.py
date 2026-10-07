"""Sonda treinada: pesos em .npz -> probabilidades por classe e confiança da resposta."""
import numpy as np

from ptguard.sonda import Sonda, load_sonda


def make(tmp_path, temperature=1.0):
    path = tmp_path / "exemplo-e5.npz"
    # 2 features, 3 classes; a classe "b" vence quando a feature 0 é alta.
    np.savez(path, mean=np.zeros(2), scale=np.ones(2),
             coef=np.array([[0.0, 0.0], [5.0, 0.0], [0.0, 5.0]]), intercept=np.zeros(3),
             classes=np.array(["a", "b", "c"]), temperature=np.array(temperature))
    return Sonda.load(path)


def test_answer_has_the_choice_shape(tmp_path):
    sonda = make(tmp_path)
    [answer] = sonda.answers(np.array([[1.0, 0.0]]))
    assert answer["type"] == "choice" and answer["choice"] == "b"
    assert set(answer["probabilities"]) == {"a", "b", "c"}
    assert abs(sum(answer["probabilities"].values()) - 1) < 1e-3
    assert answer["answer_confidence"] == max(answer["probabilities"].values())


def test_temperature_softens_without_changing_the_choice(tmp_path):
    sharp = make(tmp_path, 1.0).answers(np.array([[1.0, 0.0]]))[0]
    soft = make(tmp_path, 3.0).answers(np.array([[1.0, 0.0]]))[0]
    assert soft["choice"] == sharp["choice"]
    assert soft["answer_confidence"] < sharp["answer_confidence"]


def test_name_and_question_come_from_the_file_name(tmp_path):
    sonda = make(tmp_path)
    assert sonda.name == "exemplo-e5" and sonda.question == "exemplo" and sonda.encoder == "e5"


def test_load_sonda_reads_from_a_given_folder_and_lists_alternatives(tmp_path):
    make(tmp_path)
    assert load_sonda("exemplo-e5", tmp_path).name == "exemplo-e5"
    try:
        load_sonda("nao-existe", tmp_path)
    except FileNotFoundError as exc:
        assert "exemplo-e5" in str(exc)
    else:
        raise AssertionError("deveria falhar")


def test_binary_sonda_answers_as_noul(tmp_path):
    """Sonda com classes false/true responde como pergunta sim/não: valor = P(sim)."""
    path = tmp_path / "prompt_injection-e5.npz"
    np.savez(path, mean=np.zeros(1), scale=np.ones(1), coef=np.array([[0.0], [3.0]]), intercept=np.zeros(2),
             classes=np.array(["false", "true"]), temperature=np.array(1.0))
    [answer] = Sonda.load(path).answers(np.array([[1.0]]))
    assert answer["type"] == "noul" and answer["noul"] > 0.9
    assert answer["answer_confidence"] == max(answer["noul"], round(1 - answer["noul"], 4))


def test_published_probe_b_loads():
    """A sonda B do artigo (results/sonda-b) carrega e tem as classes do guard."""
    from conftest import RAIZ
    sonda = Sonda.load(RAIZ / "results" / "sonda-b" / "prompt_injection-e5.npz")
    assert sorted(sonda.classes) == ["false", "true"] and sonda.coef.shape == (1, 768)
