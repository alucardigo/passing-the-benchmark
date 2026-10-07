# Passing the Benchmark, Failing the README

Code, results and page-level benchmark of the paper **"Passing the Benchmark, Failing the README: A
Negative Result on Deploying a Brazilian Portuguese Prompt-Injection Classifier"** (Rodrigo Faria, 2026).

[English](#english) · [Português](#português)

> **Warning.** The best model of this study (v3, a fine-tuned multilingual-e5-large) detects 94.7% of the
> native pt-BR injections of the Weni test set, **but raised a false alarm on 217 of 217 technical
> documentation pages** (package READMEs) at every threshold from 0.5 to 0.999. The retrained v6 brings
> page false alarms down to 19–35% and loses pt-BR detection (63.7%). **No version is fit to filter web
> pages or documentation.** The agent hook in `integrations/` is a disabled reference example.

---

## English

### What this is

A one-week, fully traced case study of building a prompt-injection classifier ("guard") for Brazilian
Portuguese from open data only, and of what happened when it was evaluated the way an agent hook would
use it: page by page, not sentence by sentence.

- **Paper:** [`paper/passing-the-benchmark-en.pdf`](paper/passing-the-benchmark-en.pdf)
  (Portuguese: [`paper/passing-the-benchmark-pt.pdf`](paper/passing-the-benchmark-pt.pdf)); LaTeX source in `paper/`.
- **Code** (Apache-2.0): training/export pipeline with pinned dataset revisions, deterministic Opus-MT
  translation with cache, leakage filter, Kaggle notebook generator, sentence and page evaluators,
  public-baseline runner, page-benchmark builder, a reference agent hook (disabled), tests.
- **Results** (CC BY 4.0): one JSON per training round with the SHA-256 of the weights, per-item
  probabilities of the v3–v6 comparison, per-page and per-sentence log-odds of the baseline run. No
  third-party text.
- **Page benchmark:** a manifest with name, version, file and SHA-256 of 217 PyPI package descriptions
  plus 60 injection insertions, and a builder that downloads them from the source and refuses any page
  whose hash does not match. Rebuilt byte for byte on 2026-10-07 (217/217 benign, 60/60 with injection).

### Main findings

1. **Sentence benchmarks did not predict deployment.** v3 passes the sentence tests (Weni 94.7%,
   Wilson 95% CI 91.5–96.7; xTRam1 98.7%; 0.13–0.7% of conversational benign sentences flagged) and fails every page.
2. **It is not only our model.** Under the same page protocol, deepset/deberta-v3-base-injection also
   warned on every page, and ProtectAI v2 and Proventra mDeBERTa warned on ~15% of pages at 0.5. Of five
   public classifiers, only Llama Prompt Guard 2 86M stayed within a 2% page false-alarm budget with useful
   detection (4 of 217 pages at 0.5, Wilson 95% CI 0.7–4.6%; 62% of injected pages detected), and most of
   that detection came from the long Weni injections (93%, against 30% of the short xTRam1 ones); its
   22M sibling raised no alarm but detected 15%. Sentence and page benchmarks ranked the models in
   opposite orders (Section 5.4 of the paper, Tables 7 and 8).
3. **The diagnosis held, the fix did not.** Adding 10,000 technical benign texts (Stack Overflow,
   docstrings) removed false alarms on technical sentences (38–87% → 0%) and cut benign README windows
   flagged from 99.6% to 7.2%, but page false alarms stayed at 19–35% (worst window of ~10 per page) and
   Weni detection fell to 63.7%: part of v3's Weni score came from the same shortcut.
4. **Leakage audits matter.** v3's training set had 115 near-duplicates of Weni (58 of the 300 Weni
   texts affected; 93.4% on the 242 clean ones), and xTRam1 is not out-of-distribution for any model
   trained with ShieldLM (577 ShieldLM training rows come from xTRam1's train split).

### Results

Sentence tests (accuracy; positives only for Weni, benign only for MASSIVE-pt and Dolly-pt) and the
page test (217 benign READMEs, 60 with an injection; decision = worst window):

| round | model | Weni (300) | xTRam1 (1,500) | xTRam1-pt (500) | MASSIVE-pt (1,500) | Dolly-pt (1,000) | page false alarm |
|---|---|---|---|---|---|---|---|
| B | probe: frozen e5-base + logistic regression | 72.3% | 94.3% | 82.8% | 99.3% | — | — |
| v2 | e5-base fine-tuned | 74.3% | 98.9% | 95.4% | 99.7% | 99.6% | — |
| **v3** | **e5-large fine-tuned** | **94.7%** | 98.7% | 96.0% | 99.8% | 99.3% | **100%** at every threshold 0.5–0.999 |
| v4 | e5-base + HackAPrompt | 66.7% | 99.0% | 96.0% | 99.8% | 99.9% | — |
| v5 | e5-large + HackAPrompt | 89.7% | 99.1% | 98.0% | 100% | 99.5% | — |
| ensemble | v3 ⊕ v5 (fixed 0.5/0.5) | 91.3% | 99.0% | 96.8% | 99.9% | 99.5% | — |
| v6 | e5-large + 10k technical benign | 63.7% | 99.3% | 98.2% | 100% | 99.6% | 34.6% @0.5 · 19.4% @0.999 |

Public classifiers under the page protocol (window = what fits the model's `max_length`):

| model | false alarm / detection @0.5 | @0.99 | detection at ≤ 2% false alarm | page AUROC | Weni @0.5 | xTRam1 accuracy |
|---|---|---|---|---|---|---|
| ours, e5-large v3 (640/160 chars @ 256 tokens) | 100% / 100% | 100% / 100% | 40% | 0.857 | 94.7% | 98.7% |
| protectai/deberta-v3-base-prompt-injection-v2 (1300/200 @ 512) | 15.7% / 63% | 5.5% / 55% | 50% | 0.813 | 99.3% | 94.9% |
| proventra/mdeberta-v3-base-prompt-injection (1300/200 @ 512) | 14.7% / 70% | 8.3% / 60% | 40% | 0.883 | 79.0% | 89.6% |
| deepset/deberta-v3-base-injection (1300/200 @ 512) | 100% / 100% | 100% / 100% | 32% | 0.829 | 100% | 48.3% |
| meta-llama/Llama-Prompt-Guard-2-86M (1300/200 @ 512) | 1.8% / 62% | 0.0% / 47% | 63% | 0.956 | 93.7% | 84.7% |
| meta-llama/Llama-Prompt-Guard-2-22M (1300/200 @ 512) | 0.0% / 15% | 0.0% / 3% | 23% | 0.639 | 16.3% | 77.3% |

The two Llama Prompt Guard 2 models were measured on 2026-10-07, once access to the gated repositories
was granted, with the same script and pages on Kaggle CPU kernels (x86); their latency is not comparable
with the ARM VM used for the others. Prompt Guard v1 (`meta-llama/Prompt-Guard-86M`) is still gated and
was not evaluated. With 60 injected pages, detection differences below ~15 points are within noise. Details: [`results/`](results/README.md),
[`results/baselines/baselines.md`](results/baselines/baselines.md), [`results/v6/v6.md`](results/v6/v6.md)
(write-ups in Portuguese).

### Repository layout

```
ptguard/           library: classifier, probe, encoders, embedding cache, metrics, page windows, pinned revisions
pipeline/          treinar.py (load, translate, leakage filter, export, evaluate, probe), traduzir.py, misturar.py
kaggle/            notebook generator + notebook (fine-tuning recipe) and the Kaggle API driver (private by default)
bench/paginas/     manifesto.jsonl (names, versions, hashes), construir.py (builder), avaliar.py (page evaluator)
bench/             baselines.py (any HF classifier: page, sentence, latency), run scripts
analysis/          v3 x v6 comparison, page-leakage check, ShieldLM/test overlap counts
integrations/      claude_code/hook_guard.py: reference PostToolUse hook, fail-open, DISABLED
results/           metrics and per-item probabilities (CC BY 4.0)
paper/             LaTeX source and PDFs (CC BY 4.0)
tests/             pytest, no network or model needed
```

Code comments and identifiers are in Portuguese, the language of the study.

### Reproduce

```bash
python -m venv .venv && . .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[train,bench,test]"
pytest -q                                             # offline: no network, no model

# 1. page benchmark: downloads 217 package descriptions from PyPI (PEP 658 metadata) and the Weni/xTRam1
#    attacks from the Hugging Face Hub at pinned revisions; refuses any page whose SHA-256 differs
python bench/paginas/construir.py                     # -> work/paginas.json

# 2. public baselines on the same pages (and sentence tests, latency)
bash bench/rodar_baselines.sh                         # PG2=1 adds Llama Prompt Guard 2 (gated: accept its license)
python bench/baselines.py tabela results/baselines/por-rodada/*.json

# 3. training data for a round (v3, v5, v6 or the planned leakage-free v3-pub)
python pipeline/treinar.py exportar --rodada v6 --saida work/v6

# 4. fine-tune on Kaggle (2x T4; ~2-3.5 h for e5-large). The dataset is created PRIVATE: it contains
#    third-party text. Keep it that way.
python kaggle/gerar_notebook.py
KAGGLE_USERNAME=<you> python kaggle/publicar.py dados --arquivo work/v6/treino.jsonl
KAGGLE_USERNAME=<you> python kaggle/publicar.py treinar
KAGGLE_USERNAME=<you> python kaggle/publicar.py baixar --saida work/v6/saida

# 5. evaluate (sentence tests, then pages)
python pipeline/treinar.py avaliar work/v6/saida/guard-e5large --testes weni,xtram1,xtram1-pt,massive_pt,dolly-pt,fumaca
python bench/paginas/avaliar.py work/v6/saida/guard-e5large --janela 640 --sobra 160
```

Environment of the study: Python 3.12, numpy 2.5, scikit-learn 1.9, torch 2.14 (CPU), transformers 5.18,
datasets 5.0, huggingface_hub 1.33; fine-tuning used the Kaggle GPU image of October 2026.

Notes on exactness: dataset and model revisions are pinned in `ptguard/revisoes.json`, but they were
captured on 2026-10-06, after the runs (the original code did not pin them). Opus-MT outputs can differ
slightly across library versions and hardware, which changes the translated part of the training set;
the translation cache of a run is what makes it exact (re-exporting v3 with the study's cache, offline,
reproduced the original training file record for record: 23,693 examples in the same order). The HackAPrompt rounds (v4/v5) read an unlicensed
mirror; this code reads the MIT origin, and the equivalence of the two subsets has not been verified.
Fine-tuned weights are not in this repository; the plan is to publish a leakage-free `v3-pub` on the
Hugging Face Hub with a model card that opens with the page-level failure.

### Data and licenses

- Code: Apache-2.0 ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE)). Paper, results and benchmark manifest:
  CC BY 4.0 ([`LICENSE-CC-BY-4.0.md`](LICENSE-CC-BY-4.0.md)).
- No third-party text is redistributed: datasets, models and README pages are downloaded from their
  sources. Two evaluation sets (Weni, xTRam1) declare no license and are used for evaluation only.
  Every dataset, model and revision, with its license, is in [`ATTRIBUTION.md`](ATTRIBUTION.md).

### Citation

```bibtex
@misc{faria2026passing,
  title        = {Passing the Benchmark, Failing the README: A Negative Result on Deploying a
                  Brazilian Portuguese Prompt-Injection Classifier},
  author       = {Faria, Rodrigo},
  year         = {2026},
  howpublished = {\url{https://github.com/alucardigo/passing-the-benchmark}},
  note         = {Preprint}
}
```

See also [`CITATION.cff`](CITATION.cff).

### Author

Rodrigo Faria, independent researcher · GitHub [alucardigo](https://github.com/alucardigo) ·
LinkedIn [faria-rodrigo](https://www.linkedin.com/in/faria-rodrigo).
Much of the experimental code, the logging and the first draft of the paper were produced with an LLM
coding agent; every reported number is traced to a log line, result file or commit.

---

## Português

### O que é

Um estudo de caso de uma semana, totalmente rastreado, da construção de um classificador de prompt
injection ("guard") para o português do Brasil usando só dados abertos, e do que aconteceu quando ele foi
avaliado do jeito que um hook de agente o usaria: página a página, não frase a frase.

- **Artigo:** [`paper/passing-the-benchmark-pt.pdf`](paper/passing-the-benchmark-pt.pdf) (inglês:
  [`paper/passing-the-benchmark-en.pdf`](paper/passing-the-benchmark-en.pdf)); fonte LaTeX em `paper/`.
- **Código** (Apache-2.0): pipeline de treino e exportação com revisões fixadas, tradução determinística
  (Opus-MT) com cache, trava anti-vazamento, gerador do notebook do Kaggle, avaliação por frase e por
  página, comparação com classificadores públicos, construtor do benchmark por página, hook de exemplo
  (desligado) e testes.
- **Resultados** (CC BY 4.0): um JSON por rodada com o sha256 dos pesos, probabilidades por item da
  comparação v3 x v6, log-odds por página e por frase dos baselines. Nenhum texto de terceiro.
- **Benchmark por página:** manifesto com nome, versão, arquivo e sha256 de 217 descrições de pacotes do
  PyPI mais 60 inserções de ataque, e um construtor que baixa tudo da fonte e recusa página cujo hash não
  bate. Remontado byte a byte em 07/10/2026 (217/217 benignas, 60/60 com injeção).

### Principais achados

1. **O benchmark de frase não previu o uso real.** A v3 passa nos testes de frase (Weni 94,7%, IC 95% de
   Wilson 91,5–96,7; xTRam1 98,7%; 0,13–0,7% de aviso falso em frase benigna conversacional) e reprova em
   todas as páginas.
2. **Não é só o nosso modelo.** No mesmo protocolo, o deepset/deberta-v3-base-injection também avisou em
   toda página, e ProtectAI v2 e Proventra mDeBERTa avisaram em ~15% das páginas a 0,5. Dos cinco
   classificadores públicos, só o Llama Prompt Guard 2 86M ficou dentro de 2% de aviso falso por página com
   detecção útil (4 de 217 páginas a 0,5, IC 95% de Wilson 0,7–4,6%; 62% das páginas com injeção
   detectadas), e quase toda essa detecção veio das injeções longas do Weni (93%, contra 30% das curtas do
   xTRam1); o irmão 22M não avisou, mas detectou 15%. Frase e página ordenaram os modelos em sentidos
   opostos (seção 5.4 do artigo, Tabelas 7 e 8).
3. **O diagnóstico se confirmou, a correção não.** Acrescentar 10.000 textos técnicos benignos
   (StackOverflow, docstrings) zerou o aviso falso em frase técnica (38–87% → 0%) e derrubou as janelas
   de README marcadas de 99,6% para 7,2%, mas o aviso falso por página ficou em 19–35% (pior de ~10 janelas
   por página) e a detecção no Weni caiu para 63,7%: parte do acerto da v3 no Weni vinha do mesmo atalho.
4. **Auditoria de vazamento importa.** O treino da v3 tinha 115 quase-duplicatas do Weni (58 dos 300
   textos afetados; 93,4% nos 242 limpos), e o xTRam1 não é fora da distribuição para quem treinou com o
   ShieldLM (577 linhas do treino do ShieldLM vêm do treino do xTRam1).

As tabelas de resultados estão na seção em inglês acima (os números são os mesmos) e, com mais detalhe,
em [`results/`](results/README.md).

### Como reproduzir

Os comandos são os da seção [Reproduce](#reproduce). Em resumo: `pip install -e ".[train,bench,test]"`,
`pytest -q`, `python bench/paginas/construir.py` (monta as páginas e confere os hashes),
`bash bench/rodar_baselines.sh` (com `PG2=1` entra o Llama Prompt Guard 2, que exige aceitar a licença
dele no Hub), `python pipeline/treinar.py exportar --rodada v6 --saida work/v6`,
treino no Kaggle com `kaggle/publicar.py` (dataset **privado**: contém texto de terceiros) e avaliação com
`pipeline/treinar.py avaliar` e `bench/paginas/avaliar.py`.

Ressalvas de exatidão: as revisões de bases e modelos em `ptguard/revisoes.json` foram capturadas em
06/10/2026, depois das rodadas; a saída do Opus-MT pode variar entre versões de biblioteca e hardware (o
cache de tradução é o que torna uma rodada exata: reexportar a v3 com o cache do estudo reproduziu o
arquivo de treino original registro a registro, 23.693 exemplos na mesma ordem); as rodadas com HackAPrompt (v4/v5) leram um espelho
sem licença, e este código lê a origem MIT, sem a equivalência conferida. Os pesos não estão aqui: o plano
é publicar no Hugging Face uma `v3-pub` sem vazamento, com model card que abre pela falha em página.

### Dados e licenças

Código sob Apache-2.0; artigo, resultados e manifesto do benchmark sob CC BY 4.0. Nenhum texto de
terceiro é redistribuído: bases, modelos e páginas são baixados da fonte. Weni e xTRam1 não declaram
licença e são usados só para avaliação. Todas as bases, modelos e revisões, com licença, estão em
[`ATTRIBUTION.md`](ATTRIBUTION.md). O código tem comentários e identificadores em português.

### Citação e autor

Use a entrada BibTeX da seção [Citation](#citation) ou o [`CITATION.cff`](CITATION.cff).
Rodrigo Faria, pesquisador independente · GitHub [alucardigo](https://github.com/alucardigo) ·
LinkedIn [faria-rodrigo](https://www.linkedin.com/in/faria-rodrigo).
Boa parte do código experimental, dos registros e do primeiro rascunho do artigo foi produzida com um
agente de programação baseado em LLM; todo número relatado tem rastro em log, arquivo de resultado ou commit.
