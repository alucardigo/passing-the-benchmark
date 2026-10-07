"""Sobreposição exata (texto normalizado) entre o recorte de treino do ShieldLM e os testes do estudo.
Só contagens; nenhum texto de base é impresso (só o começo do card do TrustAIRLab). Dado público.

    python analysis/sobreposicao.py

Achados de 06/10/2026 (revisões de ptguard/revisoes.json): 577 linhas `safeguard/*` do recorte de treino
do ShieldLM estão no split train do xTRam1; 4 dos 1.500 itens de teste do xTRam1 e 14 dos 262 do teste
jackhhao aparecem literalmente no recorte; deepset 0/116.
"""
import re
import sys
from pathlib import Path

from datasets import load_dataset as _load_dataset
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ptguard.config import revisao  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def load_dataset(repo, *args, **kw):
    return _load_dataset(repo, *args, revision=revisao(repo), **kw)


norm = lambda t: re.sub(r"\s+", " ", str(t)).strip().lower()

sh = load_dataset("dmilush/shieldlm-prompt-injection")
tr = [r for r in sh["train"] if r.get("text")][:4000]
tr_set = {norm(r["text"]) for r in tr}
tr_safe = {norm(r["text"]) for r in tr if r["source"].startswith("safeguard")}

xt = load_dataset("xTRam1/safe-guard-prompt-injection")
print("xTRam1 splits", {k: len(v) for k, v in xt.items()})
xt_te = [norm(r["text"]) for r in xt["test"]][:1500]
xt_tr = {norm(r["text"]) for r in xt["train"]}
print("xTRam1 teste (1500 usados) presentes no recorte ShieldLM:", sum(t in tr_set for t in xt_te))
print("linhas 'safeguard' do recorte ShieldLM que estão no TREINO do xTRam1:", sum(t in xt_tr for t in tr_safe), "/", len(tr_safe))
print("linhas 'safeguard' do recorte ShieldLM que estão no TESTE do xTRam1:", sum(t in set(xt_te) or t in {norm(r['text']) for r in xt['test']} for t in tr_safe))

dp = load_dataset("deepset/prompt-injections")
dp_te = [norm(r["text"]) for r in dp["test"]]
print("deepset teste presentes no recorte ShieldLM:", sum(t in tr_set for t in dp_te), "/", len(dp_te))
jk = load_dataset("jackhhao/jailbreak-classification")
jk_te = [norm(r["prompt"]) for r in jk["test"]]
print("jackhhao teste presentes no recorte ShieldLM:", sum(t in tr_set for t in jk_te), "/", len(jk_te))
sh_te = [norm(r["text"]) for r in sh["test"] if r.get("text")][:4000]
print("ShieldLM teste (4000) presentes no recorte de treino ShieldLM:", sum(t in tr_set for t in sh_te))

# TrustAIRLab: o que o card diz da licença
p = hf_hub_download("TrustAIRLab/in-the-wild-jailbreak-prompts", "README.md", repo_type="dataset")
t = open(p, encoding="utf-8").read()
print("== TrustAIRLab front-matter/licença ==")
print(t[:400])
for linha in t.splitlines():
    if re.search(r"licen", linha, re.I):
        print("  ", linha[:240])
