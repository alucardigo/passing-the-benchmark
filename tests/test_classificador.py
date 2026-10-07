"""Classificador ajustado (pasta HF) responde no mesmo formato da sonda."""
import json

import numpy as np

from ptguard.classificador import Classificador


class FakeModel:
    """Logits fixos: a classe 'b' vence. Substitui o forward do transformers no teste."""
    def __call__(self, texts):
        return np.array([[0.0, 3.0, 0.0]] * len(texts))


def test_answers_have_choice_shape_and_apply_temperature(tmp_path):
    (tmp_path / "laya-classificador.json").write_text(json.dumps({"temperatura": 2.0}), encoding="utf-8")
    clf = Classificador(name="exemplo-e5ft", labels=["a", "b", "c"], temperature=2.0, forward=FakeModel())
    [ans] = clf.answers(["texto"])
    assert ans["type"] == "choice" and ans["choice"] == "b"
    sharp = Classificador(name="exemplo-e5ft", labels=["a", "b", "c"], temperature=1.0, forward=FakeModel())
    assert ans["answer_confidence"] < sharp.answers(["texto"])[0]["answer_confidence"]
    assert ans["fonte"] == "classificador:exemplo-e5ft"


def test_binary_classifier_answers_as_noul():
    """Classificador false/true (guard) responde como pergunta sim/não: valor = P(sim)."""
    class Fixed:
        def __call__(self, texts):
            return np.array([[0.0, 3.0]] * len(texts))
    [ans] = Classificador(name="pi", labels=["false", "true"], temperature=1.0, forward=Fixed()).answers(["x"])
    assert ans["type"] == "noul" and ans["noul"] > 0.9
