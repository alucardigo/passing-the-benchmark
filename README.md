# Passing the Benchmark, Failing the README

Code, results and page-level benchmark of the paper **"Passing the Benchmark, Failing the README: Leakage
and Shortcut Learning in a Brazilian Portuguese Prompt-Injection Classifier"** (Rodrigo Faria, 2026).

[English](#english) · [Português](#português)

> **Warning.** The best model of this study (v3, a fine-tuned multilingual-e5-large) detected 94.7% of the
> native pt-BR injections of the Weni test set, **but that figure does not survive decontamination**: the same recipe
> retrained without test duplicates and near-duplicates (v3-pub) detects 68.0%. **Both raised a false alarm
> on 217 of 217 technical documentation pages** (package READMEs) at every threshold from 0.5 to 0.999. The
> retrained v6 brings page false alarms down to 19–35% and detects 63.7% of Weni, close to v3-pub. **No
> version is fit to filter web pages or documentation.** The agent hook in `integrations/` is a disabled
> reference example.

---

## English

### What this is

A fully traced case study of building a prompt-injection classifier ("guard") for Brazilian Portuguese
from open data only, of what happened when it was evaluated the way an agent hook would use it (page by
page, not sentence by sentence), and of what a decontaminated retraining revealed about its benchmark score.

- **Paper:** [`paper/passing-the-benchmark-en.pdf`](paper/passing-the-benchmark-en.pdf)
  (Portuguese: [`paper/passing-the-benchmark-pt.pdf`](paper/passing-the-benchmark-pt.pdf)); LaTeX source in `paper/`.
- **Code** (Apache-2.0): training/export pipeline with pinned dataset revisions, deterministic Opus-MT
  translation with cache, leakage filter, Kaggle notebook generator, sentence and page evaluators,
  public-baseline runner, page-benchmark builder, a reference agent hook (disabled), tests.
- **Results** (CC BY 4.0): one JSON per training round with the SHA-256 of the weights, per-item
  probabilities of the v3–v6 and v3-pub comparisons, per-page and per-sentence log-odds of the baseline run.
  No third-party text.
- **Page benchmark:** a manifest with name, version, file and SHA-256 of 217 PyPI package descriptions
  plus 60 injection insertions, and a builder that downloads them from the source and refuses any page
  whose hash does not match. Rebuilt byte for byte on 2026-10-07 (217/217 benign, 60/60 with injection).

### Main findings

1. **Sentence benchmarks did not predict deployment.** v3 passes the sentence tests (Weni 94.7%,
   Wilson 95% CI 91.5–96.7, inflated by leakage, see 4; xTRam1 98.7%; 0.13–0.7% of conversational benign
   sentences flagged) and fails every page.
2. **It is not only our model.** Under the same page protocol, deepset/deberta-v3-base-injection also
   warned on every page, and ProtectAI v2 and Proventra mDeBERTa warned on ~15% of pages at 0.5. Of five
   public classifiers, only Llama Prompt Guard 2 86M stayed within a 2% page false-alarm budget with useful
   detection (4 of 217 pages at 0.5, Wilson 95% CI 0.7–4.6%; 62% of injected pages detected), and most of
   that detection came from the long Weni injections (93%, against 30% of the short xTRam1 ones); its
   22M sibling raised no alarm but detected 15%. Sentence and page benchmarks ranked the models in
   opposite orders (Section 5.4 of the paper, Tables 8 and 9).
3. **The diagnosis held, the fix did not.** Adding 10,000 technical benign texts (Stack Overflow,
   docstrings) removed false alarms on technical sentences (38–87% → 0%) and cut benign README windows
   flagged from 99.6% to 7.2%, but page false alarms stayed at 19–35% (worst window of ~10 per page). Weni
   detection fell to 63.7%, which we first blamed on the new negatives; a decontaminated control without them
   (v3-pub) detects 68.0% (paired difference 4.3 points, McNemar p = 0.18), so the comparison with v3 cannot
   charge that drop to the new negatives. The two versions miss partly different texts, though, and only a
   control that removes just the Weni near-duplicates, not run yet, can say how much of the drop is theirs.
4. **The headline number did not survive decontamination.** v3's training set had 115 near-duplicates of Weni texts,
   exact duplicates (after normalisation) of items of almost every test (83 of 1,500 xTRam1, 20 of 262
   jackhhao, among others), and 577 ShieldLM rows taken from xTRam1's train split. A cosine-similarity cut
   put the effect on Weni at 1.3 points. Retraining the same recipe without the duplicates, their
   translations, the near-duplicates, the xTRam1 rows and the licence-excluded ShieldLM rows (v3-pub) costs
   26.7 points on Weni (94.7% → 68.0%, McNemar p < 1e-6) and 3.3 on xTRam1 (98.7% → 95.4%), and leaves the
   page failure untouched (217/217). v3-pub drops more on the Weni texts without a near-duplicate in training
   (29.8 points) than on those with one (13.8), so the 26.7 points bound the leakage effect from above rather
   than measure it: v3-pub also has
   967 fewer attack examples, 513 of them duplicates of other tests, and a control that removes only the 115
   near-duplicates has not been run.

### Results

Sentence tests (accuracy; positives only for Weni, benign only for MASSIVE-pt and Dolly-pt) and the
page test (217 benign READMEs, 60 with an injection; decision = worst window):

| round | model | Weni (300) | xTRam1 (1,500) | xTRam1-pt (500) | MASSIVE-pt (1,500) | Dolly-pt (1,000) | page false alarm |
|---|---|---|---|---|---|---|---|
| B | probe: frozen e5-base + logistic regression | 72.3% | 94.3% | 82.8% | 99.3% | — | — |
| v2 | e5-base fine-tuned | 74.3% | 98.9% | 95.4% | 99.7% | 99.6% | — |
| **v3** | **e5-large fine-tuned** | **94.7%** † | 98.7% | 96.0% | 99.8% | 99.3% | **100%** at every threshold 0.5–0.999 |
| v4 | e5-base + HackAPrompt | 66.7% | 99.0% | 96.0% | 99.8% | 99.9% | — |
| v5 | e5-large + HackAPrompt | 89.7% | 99.1% | 98.0% | 100% | 99.5% | — |
| ensemble | v3 ⊕ v5 (fixed 0.5/0.5) | 91.3% | 99.0% | 96.8% | 99.9% | 99.5% | — |
| v6 | e5-large + 10k technical benign | 63.7% | 99.3% | 98.2% | 100% | 99.6% | 34.6% @0.5 · 19.4% @0.999 |
| **v3-pub** | **e5-large, decontaminated** (no test duplicates, translations, Weni near-duplicates, xTRam1 rows or licence-excluded rows) | **68.0%** | 95.4% | 94.8% | 99.9% | 99.8% | **100%** at every threshold 0.5–0.999 |

† Does not survive decontamination: v3-pub, the same recipe on decontaminated data, detects 68.0% (Wilson 95% CI 62.5–73.0;
v3 alone detects 81 texts that v3-pub misses, the reverse happens once). Details in
[`results/v3pub/v3pub.md`](results/v3pub/v3pub.md) and in Section 4(d) and Table 5 of the paper.

Public classifiers under the page protocol (window = what fits the model's `max_length`):

| model | false alarm / detection @0.5 | @0.99 | detection at ≤ 2% false alarm | page AUROC | Weni @0.5 | xTRam1 accuracy |
|---|---|---|---|---|---|---|
| ours, e5-large v3 (640/160 chars @ 256 tokens) | 100% / 100% | 100% / 100% | 40% | 0.857 | 94.7% † | 98.7% |
| protectai/deberta-v3-base-prompt-injection-v2 (1300/200 @ 512) | 15.7% / 63% | 5.5% / 55% | 50% | 0.813 | 99.3% | 94.9% |
| proventra/mdeberta-v3-base-prompt-injection (1300/200 @ 512) | 14.7% / 70% | 8.3% / 60% | 40% | 0.883 | 79.0% | 89.6% |
| deepset/deberta-v3-base-injection (1300/200 @ 512) | 100% / 100% | 100% / 100% | 32% | 0.829 | 100% | 48.3% |
| meta-llama/Llama-Prompt-Guard-2-86M (1300/200 @ 512) | 1.8% / 62% | 0.0% / 47% | 63% | 0.956 | 93.7% | 84.7% |
| meta-llama/Llama-Prompt-Guard-2-22M (1300/200 @ 512) | 0.0% / 15% | 0.0% / 3% | 23% | 0.639 | 16.3% | 77.3% |

The two Llama Prompt Guard 2 models were measured on 2026-10-07, once access to the gated repositories
was granted, with the same script and pages on Kaggle CPU kernels (x86); their latency is not comparable
with the ARM VM used for the others. Prompt Guard v1 (`meta-llama/Prompt-Guard-86M`) is still gated and
was not evaluated. With 60 injected pages, detection differences below ~15 points are within noise. Details: [`results/`](results/README.md),
[`results/baselines/baselines.md`](results/baselines/baselines.md), [`results/v6/v6.md`](results/v6/v6.md),
[`results/v3pub/v3pub.md`](results/v3pub/v3pub.md) (write-ups in Portuguese).

### Repository layout

```
ptguard/           library: classifier, probe, encoders, embedding cache, metrics, page windows, pinned revisions
pipeline/          treinar.py (load, translate, leakage filter, export, evaluate, probe), traduzir.py, misturar.py
kaggle/            notebook generator + notebook (fine-tuning recipe) and the Kaggle API driver (private by default)
bench/paginas/     manifesto.jsonl (names, versions, hashes), construir.py (builder), avaliar.py (page evaluator)
bench/             baselines.py (any HF classifier: page, sentence, latency), run scripts
analysis/          two-version comparison (v3 x v6), page-leakage check, ShieldLM/test overlap counts
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

# 3. training data for a round (v3, v5, v6 or v3-pub; the v3-pub round here approximates the study's export:
#    it drops only ShieldLM's safeguard/* rows and does not apply the translation-pair rule)
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
Fine-tuned weights are not in this repository: `v3-pub` (trained 2026-10-07; Weni 68.0%, page false alarms
217/217) and the round-B probe are published under MIT on Kaggle Models as `passing-the-benchmark-guard`, with a
model card that opens with the page-level failure and reports v3-pub's own numbers.

### Data and licenses

- Code: Apache-2.0 ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE)). Paper, results and benchmark manifest:
  CC BY 4.0 ([`LICENSE-CC-BY-4.0.md`](LICENSE-CC-BY-4.0.md)). Model weights: MIT (the probe-B weights in
  [`results/sonda-b/`](results/sonda-b/LICENSE) and the fine-tuned v3-pub weights on Kaggle Models).
- No third-party text is redistributed: datasets, models and README pages are downloaded from their
  sources. Two evaluation sets (Weni, xTRam1) declare no license and are used for evaluation only.
  Every dataset, model and revision, with its license, is in [`ATTRIBUTION.md`](ATTRIBUTION.md).

### Citation

```bibtex
@misc{faria2026passing,
  title        = {Passing the Benchmark, Failing the README: Leakage and Shortcut Learning in a
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

Um estudo de caso totalmente rastreado da construção de um classificador de prompt injection ("guard")
para o português do Brasil usando só dados abertos, do que aconteceu quando ele foi avaliado do jeito que um
hook de agente o usaria (página a página, não frase a frase) e do que um retreino descontaminado revelou
sobre o seu placar no benchmark.

- **Artigo:** [`paper/passing-the-benchmark-pt.pdf`](paper/passing-the-benchmark-pt.pdf) (inglês:
  [`paper/passing-the-benchmark-en.pdf`](paper/passing-the-benchmark-en.pdf)); fonte LaTeX em `paper/`.
- **Código** (Apache-2.0): pipeline de treino e exportação com revisões fixadas, tradução determinística
  (Opus-MT) com cache, trava anti-vazamento, gerador do notebook do Kaggle, avaliação por frase e por
  página, comparação com classificadores públicos, construtor do benchmark por página, hook de exemplo
  (desligado) e testes.
- **Resultados** (CC BY 4.0): um JSON por rodada com o sha256 dos pesos, probabilidades por item das
  comparações v3 x v6 e com a v3-pub, log-odds por página e por frase dos baselines. Nenhum texto de terceiro.
- **Benchmark por página:** manifesto com nome, versão, arquivo e sha256 de 217 descrições de pacotes do
  PyPI mais 60 inserções de ataque, e um construtor que baixa tudo da fonte e recusa página cujo hash não
  bate. Remontado byte a byte em 07/10/2026 (217/217 benignas, 60/60 com injeção).

### Principais achados

1. **O benchmark de frase não previu o uso real.** A v3 passa nos testes de frase (Weni 94,7%, IC 95% de
   Wilson 91,5–96,7, inflado por vazamento, ver 4; xTRam1 98,7%; 0,13–0,7% de aviso falso em frase benigna
   conversacional) e reprova em todas as páginas.
2. **Não é só o nosso modelo.** No mesmo protocolo, o deepset/deberta-v3-base-injection também avisou em
   toda página, e ProtectAI v2 e Proventra mDeBERTa avisaram em ~15% das páginas a 0,5. Dos cinco
   classificadores públicos, só o Llama Prompt Guard 2 86M ficou dentro de 2% de aviso falso por página com
   detecção útil (4 de 217 páginas a 0,5, IC 95% de Wilson 0,7–4,6%; 62% das páginas com injeção
   detectadas), e quase toda essa detecção veio das injeções longas do Weni (93%, contra 30% das curtas do
   xTRam1); o irmão 22M não avisou, mas detectou 15%. Frase e página ordenaram os modelos em sentidos
   opostos (seção 5.4 do artigo, Tabelas 8 e 9).
3. **O diagnóstico se confirmou, a correção não.** Acrescentar 10.000 textos técnicos benignos
   (StackOverflow, docstrings) zerou o aviso falso em frase técnica (38–87% → 0%) e derrubou as janelas
   de README marcadas de 99,6% para 7,2%, mas o aviso falso por página ficou em 19–35% (pior de ~10 janelas
   por página). A detecção no Weni caiu para 63,7%, o que atribuímos primeiro aos negativos novos; um
   controle descontaminado sem eles (v3-pub) detecta 68,0% (diferença pareada de 4,3 pontos, McNemar
   p = 0,18), então a comparação com a v3 não permite cobrar essa queda dos negativos novos. As duas versões,
   porém, erram textos em parte diferentes, e só um controle que tire apenas as quase-duplicatas do Weni,
   ainda não rodado, pode dizer quanto da queda é deles.
4. **O número principal não sobreviveu à descontaminação.** O treino da v3 tinha 115 quase-duplicatas de textos do Weni,
   duplicatas exatas (após normalização) de itens de quase todo teste (83 de 1.500 no xTRam1, 20 de 262 no
   jackhhao, entre outros) e 577 linhas do ShieldLM tiradas do treino do xTRam1. Um corte de similaridade de
   cosseno estimava o efeito no Weni em 1,3 ponto. Retreinar a mesma receita sem as duplicatas, as traduções
   delas, as quase-duplicatas, as linhas do xTRam1 e as linhas do ShieldLM excluídas pela licença (v3-pub)
   custa 26,7 pontos no Weni (94,7% → 68,0%, McNemar p < 1e-6) e 3,3 no xTRam1 (98,7% → 95,4%), e não mexe na
   falha por página (217/217). A v3-pub cai mais nos textos do Weni sem quase-duplicata no treino (29,8 pontos)
   do que nos que têm uma (13,8), então os 26,7 pontos limitam o efeito do vazamento por cima, em vez de medi-lo: a v3-pub também tem 967
   exemplos de ataque a menos, 513 deles duplicatas de outros testes, e um controle que tire só as 115
   quase-duplicatas não foi rodado.

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
sem licença, e este código lê a origem MIT, sem a equivalência conferida. A rodada `v3-pub` deste
repositório é uma aproximação da exportação do estudo (tira só as linhas `safeguard/*` do ShieldLM e não
aplica a regra de pares de tradução). Os pesos não estão aqui: a `v3-pub` (treinada em 07/10/2026; Weni 68,0%,
aviso falso em 217/217 páginas) e a sonda da rodada B estão publicadas sob MIT no Kaggle Models como
`passing-the-benchmark-guard`, com model card que abre pela falha em página e relata os números da própria
v3-pub.

### Dados e licenças

Código sob Apache-2.0; artigo, resultados e manifesto do benchmark sob CC BY 4.0; pesos de modelo sob MIT
(os da sonda B, em `results/sonda-b/`, e os ajustados da v3-pub, no Kaggle Models). Nenhum texto de
terceiro é redistribuído: bases, modelos e páginas são baixados da fonte. Weni e xTRam1 não declaram
licença e são usados só para avaliação. Todas as bases, modelos e revisões, com licença, estão em
[`ATTRIBUTION.md`](ATTRIBUTION.md). O código tem comentários e identificadores em português.

### Citação e autor

Use a entrada BibTeX da seção [Citation](#citation) ou o [`CITATION.cff`](CITATION.cff).
Rodrigo Faria, pesquisador independente · GitHub [alucardigo](https://github.com/alucardigo) ·
LinkedIn [faria-rodrigo](https://www.linkedin.com/in/faria-rodrigo).
Boa parte do código experimental, dos registros e do primeiro rascunho do artigo foi produzida com um
agente de programação baseado em LLM; todo número relatado tem rastro em log, arquivo de resultado ou commit.
