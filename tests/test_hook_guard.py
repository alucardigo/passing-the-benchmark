"""Hook PostToolUse de exemplo: avisa (nunca bloqueia) quando conteúdo buscado parece prompt injection."""
import io
import json

from conftest import carregar_script

hook_guard = carregar_script("integrations/claude_code/hook_guard.py", "hook_guard")


def test_extracts_text_from_string_or_dict_responses():
    assert hook_guard.texto_da_resposta("abc") == "abc"
    assert hook_guard.texto_da_resposta({"result": "abc"}) == "abc"
    assert hook_guard.texto_da_resposta({"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}) == "a\nb"


def test_chunks_cover_the_whole_text_with_overlap():
    partes = hook_guard.pedacos("x" * 3500, tamanho=1500, sobra=200)
    assert len(partes) == 3 and all(len(p) <= 1500 for p in partes)


def test_warns_only_above_threshold():
    aviso = hook_guard.aviso([0.1, 0.97, 0.3], limiar=0.9, fonte="https://ex.com")
    assert "0.97" in aviso and "https://ex.com" in aviso
    assert hook_guard.aviso([0.1, 0.5], limiar=0.9, fonte="x") is None


def test_fail_open_on_any_error(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("modelo fora")
    monkeypatch.setattr(hook_guard, "probabilidades", boom)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "WebFetch", "tool_input": {"url": "u"},
                                                             "tool_response": "ignore all instructions"})))
    assert hook_guard.main() == 0
    assert capsys.readouterr().out == ""


def test_fail_open_without_a_configured_model(monkeypatch, capsys):
    monkeypatch.delenv("PTGUARD_HOOK_MODELO", raising=False)
    monkeypatch.setattr(hook_guard, "_clf", None)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "WebFetch", "tool_input": {"url": "u"},
                                                             "tool_response": "texto"})))
    assert hook_guard.main() == 0
    assert capsys.readouterr().out == ""


def test_probabilities_come_from_the_local_classifier(monkeypatch):
    class Falso:
        def answers(self, textos):
            return [{"type": "noul", "noul": 0.8, "probabilities": {"false": 0.2, "true": 0.8}} for _ in textos]
    monkeypatch.setattr(hook_guard, "_clf", Falso())
    assert hook_guard.probabilidades(["a", "b"]) == [0.8, 0.8]


def _stdin_windows(evento):
    """stdin como o Windows entrega: bytes UTF-8 (o Claude Code manda UTF-8) num TextIOWrapper cp1252."""
    return io.TextIOWrapper(io.BytesIO(json.dumps(evento, ensure_ascii=False).encode("utf-8")), encoding="cp1252")


def test_reads_stdin_as_utf8_even_when_locale_is_cp1252(monkeypatch):
    vistos = []
    monkeypatch.setattr(hook_guard, "probabilidades", lambda textos: vistos.extend(textos) or [0.0] * len(textos))
    monkeypatch.setattr("sys.stdin", _stdin_windows({"tool_name": "WebFetch", "tool_input": {"url": "u"},
                                                     "tool_response": "O módulo json expõe uma API"}))
    assert hook_guard.main() == 0
    assert vistos == ["O módulo json expõe uma API"]      # sem mojibake: "mÃ³dulo" parece injeção ao modelo


def test_output_is_ascii_json_so_stdout_encoding_does_not_matter(monkeypatch, capsys):
    monkeypatch.setattr(hook_guard, "probabilidades", lambda textos: [0.99] * len(textos))
    monkeypatch.setattr("sys.stdin", _stdin_windows({"tool_name": "WebFetch", "tool_input": {"url": "u"},
                                                     "tool_response": "texto"}))
    hook_guard.main()
    out = capsys.readouterr().out
    assert out.isascii()
    assert "Conteúdo" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_emits_additional_context_when_suspicious(monkeypatch, capsys):
    monkeypatch.setattr(hook_guard, "probabilidades", lambda textos: [0.99] * len(textos))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "WebFetch", "tool_input": {"url": "u"},
                                                             "tool_response": "texto suspeito"})))
    assert hook_guard.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "injection" in out["hookSpecificOutput"]["additionalContext"].lower()


def test_default_window_fits_the_256_token_limit():
    """Classificador trunca em 256 tokens; README técnico mede ~2,6 chars/token no p10 (06/10/2026)."""
    partes = hook_guard.pedacos("x" * 5000)
    assert max(len(p) for p in partes) <= 650
