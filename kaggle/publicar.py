"""Ajuste fino no Kaggle pela API oficial (sem interface): dados -> treinar -> status -> baixar.

    export KAGGLE_USERNAME=<seu usuário>
    python kaggle/publicar.py dados   --arquivo work/v6/treino.jsonl   # dataset PRIVADO com o treino (cria ou versiona)
    python kaggle/publicar.py treinar                                  # envia kaggle/guard-treino.ipynb, GPU + internet
    python kaggle/publicar.py status                                   # estado da execução
    python kaggle/publicar.py baixar  --saida work/v6/saida            # saídas (zips dos modelos)

Opções: --dataset SLUG --kernel SLUG --notebook ARQ.ipynb --arquivo treino.jsonl --saida DIR

Autenticação: `python -m kaggle auth login` (ou kaggle.json). O dataset e o kernel nascem PRIVADOS.
Mantenha assim: o treino.jsonl contém texto de bases de terceiros (uma delas sem licença declarada,
dentro do ShieldLM) e traduções; redistribuir esse arquivo não é o mesmo que publicar os pesos.
Validação final e testes nunca sobem: a avaliação é local.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATASET_PADRAO = "ptguard-treino"
KERNEL_PADRAO = "ptguard-finetune"
NOTEBOOK_PADRAO = RAIZ / "kaggle" / "guard-treino.ipynb"
TREINO_PADRAO = RAIZ / "work" / "v6" / "treino.jsonl"
SAIDA_PADRAO = RAIZ / "work" / "kaggle-saida"


def kaggle(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise SystemExit(f"kaggle {' '.join(args)} falhou:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}")
    return proc


def dados(a) -> None:
    if not a.arquivo.exists():
        raise SystemExit(f"{a.arquivo} não existe: rode `pipeline/treinar.py exportar` antes")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(a.arquivo, Path(tmp) / "treino.jsonl")
        meta = {"title": a.dataset.split("/")[1], "id": a.dataset, "licenses": [{"name": "other"}]}
        (Path(tmp) / "dataset-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        existe = kaggle("datasets", "status", a.dataset, check=False).returncode == 0
        if existe:
            out = kaggle("datasets", "version", "-p", tmp, "-m", "treino atualizado")
        else:
            out = kaggle("datasets", "create", "-p", tmp)          # privado por padrão (sem --public)
    print(out.stdout.strip()[-400:])


def treinar(a) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(a.notebook, Path(tmp) / a.notebook.name)
        meta = {"id": a.kernel, "title": a.kernel.split("/")[1], "code_file": a.notebook.name, "language": "python",
                "kernel_type": "notebook", "is_private": True, "enable_gpu": True, "enable_tpu": False,
                "enable_internet": True, "dataset_sources": [a.dataset], "competition_sources": [],
                "kernel_sources": [], "model_sources": []}
        (Path(tmp) / "kernel-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        print(kaggle("kernels", "push", "-p", tmp).stdout.strip()[-400:])


def status(a) -> None:
    print(kaggle("kernels", "status", a.kernel).stdout.strip())


def baixar(a) -> None:
    a.saida.mkdir(parents=True, exist_ok=True)
    print(kaggle("kernels", "output", a.kernel, "-p", str(a.saida), "--force").stdout.strip()[-600:])


def _args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dados", "treinar", "status", "baixar"])
    ap.add_argument("--usuario", default=os.environ.get("KAGGLE_USERNAME"))
    ap.add_argument("--dataset", default=DATASET_PADRAO)
    ap.add_argument("--kernel", default=KERNEL_PADRAO)
    ap.add_argument("--notebook", type=Path, default=NOTEBOOK_PADRAO)
    ap.add_argument("--arquivo", type=Path, default=TREINO_PADRAO)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    a = ap.parse_args()
    if not a.usuario:
        raise SystemExit("defina KAGGLE_USERNAME (ou --usuario)")
    a.dataset = a.dataset if "/" in a.dataset else f"{a.usuario}/{a.dataset}"
    a.kernel = a.kernel if "/" in a.kernel else f"{a.usuario}/{a.kernel}"
    return a


if __name__ == "__main__":
    args = _args()
    {"dados": dados, "treinar": treinar, "status": status, "baixar": baixar}[args.cmd](args)
