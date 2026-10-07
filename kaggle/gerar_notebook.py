"""Gera o notebook de ajuste fino do classificador binário do guard para o Kaggle.

    python kaggle/gerar_notebook.py               -> kaggle/guard-treino.ipynb (e5-large, a receita do v3/v5/v6)
    python kaggle/gerar_notebook.py e5base e5large                             (as duas bases, em sequência)

Entrada no Kaggle: um dataset com treino.jsonl ({"texto", "rotulo": "true"|"false"}), exportado por
`pipeline/treinar.py exportar --rodada <v3|v5|v6|v3-pub>`. Treina multilingual-e5-base e/ou -large e salva
cada um em fp16 + zip. A avaliação é local (`pipeline/treinar.py avaliar <pasta>`), nos testes, que
nunca sobem para o Kaggle.
"""
import json
import sys
from pathlib import Path

# nome -> (repo, lote, acumulação). Large com lote 8 x 4: com 16 x 2 deu OOM no T4 (14,5 GB) após o base.
MODELOS = {"e5base": ("intfloat/multilingual-e5-base", 32, 1), "e5large": ("intfloat/multilingual-e5-large", 8, 4)}
PADRAO = ("e5large",)
SKILL = "guard"


def cells(skill: str, modelos: dict):
    return [
        ("markdown", f"# passing-the-benchmark: ajuste fino binário do `{skill}`\n\n"
                     "multilingual-e5 (base e/ou large), 3 épocas, lr 2e-5, fp16, `max_length` 256, prefixo `query: `, "
                     "validação de 8% estratificada (seed 0)."),
        ("code", """import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'   # antes do CUDA iniciar: evita fragmentação
import torch
assert torch.cuda.is_available(), 'SEM GPU: ligar o acelerador antes de treinar'
!nvidia-smi --query-gpu=name,memory.total --format=csv
import glob
DATA = glob.glob('/kaggle/input/**/treino.jsonl', recursive=True)[0]
print(DATA)"""),
        ("code", f"""import json, numpy as np
from datasets import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding,
                          Trainer, TrainingArguments)
rows = [json.loads(l) for l in open(DATA)]
labels = ['false', 'true']
MODELOS = {json.dumps(modelos)}
for nome, (repo, bs, acc) in MODELOS.items():
    tok = AutoTokenizer.from_pretrained(repo)
    ds = Dataset.from_dict({{'text': ['query: ' + r['texto'] for r in rows], 'label': [labels.index(r['rotulo']) for r in rows]}})
    ds = ds.class_encode_column('label').train_test_split(test_size=0.08, seed=0, stratify_by_column='label')
    ds = ds.map(lambda b: tok(b['text'], truncation=True, max_length=256), batched=True)
    model = AutoModelForSequenceClassification.from_pretrained(repo, num_labels=2,
              id2label=dict(enumerate(labels)), label2id={{l: i for i, l in enumerate(labels)}})
    # aquecimento em passos explícitos: o transformers da imagem do Kaggle (out/2026) removeu warmup_ratio
    passos = (len(ds['train']) // (bs * acc) + 1) * 3
    args = TrainingArguments(output_dir=f'/kaggle/working/tmp-{{nome}}', per_device_train_batch_size=bs,
              gradient_accumulation_steps=acc, per_device_eval_batch_size=64, learning_rate=2e-5,
              num_train_epochs=3, weight_decay=0.01, warmup_steps=int(0.06 * passos), fp16=True, eval_strategy='epoch',
              save_strategy='epoch', load_best_model_at_end=True, metric_for_best_model='accuracy',
              save_total_limit=1, report_to=[], gradient_checkpointing=(nome == 'e5large'))
    trainer = Trainer(model=model, args=args, train_dataset=ds['train'], eval_dataset=ds['test'],
              data_collator=DataCollatorWithPadding(tok),
              compute_metrics=lambda p: {{'accuracy': float((p.predictions.argmax(-1) == p.label_ids).mean())}})
    trainer.train()
    print(nome, trainer.evaluate())
    out = f'/kaggle/working/{skill}-{{nome}}'
    trainer.model.half().save_pretrained(out); tok.save_pretrained(out)
    del model, trainer; torch.cuda.empty_cache()"""),
        ("code", f"""!rm -rf /kaggle/working/tmp-*
!cd /kaggle/working && for d in {' '.join(f'{skill}-{n}' for n in modelos)}; do zip -q -r $d.zip $d; done && ls -la /kaggle/working/*.zip"""),
    ]


def notebook(skill: str, modelos: dict) -> dict:
    out = []
    for kind, source in cells(skill, modelos):
        cell = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
        if kind == "code":
            cell.update({"execution_count": None, "outputs": []})
        out.append(cell)
    return {"cells": out, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                         "language_info": {"name": "python"}}}


if __name__ == "__main__":
    escolha = sys.argv[1:] or list(PADRAO)
    path = Path(__file__).with_name(f"{SKILL}-treino.ipynb")
    path.write_text(json.dumps(notebook(SKILL, {k: MODELOS[k] for k in escolha}), ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    print(path)
