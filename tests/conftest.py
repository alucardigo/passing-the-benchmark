"""Os testes rodam sem instalar o pacote: a raiz do repositório entra no sys.path."""
import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def carregar_script(caminho_relativo: str, nome: str):
    """Importa um script (pipeline/, bench/, integrations/) pelo caminho, como módulo isolado."""
    spec = importlib.util.spec_from_file_location(nome, RAIZ / caminho_relativo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
