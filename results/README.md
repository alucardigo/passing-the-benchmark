# Results / Resultados

Metrics only: no third-party text. Licensed CC BY 4.0. File names map to the rounds of the paper.
Each per-round JSON records the SHA-256 of the weights it evaluated (`sha256_pesos`). JSON fields are in
Portuguese (`acuracia` = accuracy, `aviso_falso` = false alarm, `deteccao` = detection, `teste` = test).

Só métricas, sem texto de terceiro. Licença CC BY 4.0. Os nomes seguem as rodadas do artigo.

## `guard/`: sentence-level tests, one file per round / testes por frase, um arquivo por rodada

| file | round | notes |
|---|---|---|
| `sonda-en-20261001.json` | probe 0 (frozen e5-base + logistic regression, English sources) | |
| `sonda-a-20261005.json` | round A (probe + pt-BR translations) | |
| `sonda-b-20261005.json` | round B (probe + native pt sources) | weights in `sonda-b/` |
| `v2-e5base-20261005.json` | v2, fine-tuned e5-base | same export as v3; no leak filter |
| `v3-e5large-20261006.json` | **v3**, fine-tuned e5-large | Weni 94.7%; 100% page false alarms |
| `v3-e5large-extras-20261006.json` | v3, extra tests (first 300 items) | deepset, jackhhao, SPML, technical benign |
| `v4-e5base-hackaprompt-20261006.json` | v4, e5-base + HackAPrompt | leak filter on |
| `v5-e5large-hackaprompt-20261006.json` | v5, e5-large + HackAPrompt | |
| `v5-e5large-hackaprompt-reavaliado-20261006.json` | v5 re-evaluated (per-item probabilities for the ensemble) | |
| `v3-v5-mistura-20261006.json` | fixed 0.5/0.5 log-odds ensemble of v3 and v5 | recomputed from the stored per-item probabilities (`pipeline/misturar.py`) |
| `v6-e5large-a-20261006.json`, `-b-`, `-extras-` | v6, e5-large + 10,000 technical benign texts | Weni 63.7%; page false alarms 19–35% |

`arquivo_original` keeps the file name used during the study; `rodada` names the round. The label
`laya-e5large-v3` in the baseline files is the study's name for our fine-tuned e5-large v3; it is not a
model released by the Laya project.

## `paginas/`: page-level probabilities of v3 / probabilidades por página da v3

`v3-paginas-1500-200.json` and `v3-paginas-640-160.json`: worst-window P(injection) for the 217 benign pages
and the 60 pages with an injection, by index (windows of 1,500/200 and 640/160 characters). 217 of 217
benign pages warned at every threshold from 0.5 to 0.999.

## `sonda-b/`: probe B weights / pesos da sonda B

`prompt_injection-e5.npz` (StandardScaler + logistic regression over frozen `intfloat/multilingual-e5-base`
embeddings; 17 KB; no e5 weights inside) and its metadata JSON. Loads with `ptguard.sonda.Sonda.load`.

## `baselines/`: public classifiers under the page protocol / classificadores públicos no protocolo de página

`baselines.md` (write-up, in Portuguese), `baselines.json` (all runs) and `por-rodada/` (one JSON per run).
Each run has the configuration, Hub revision, metrics per threshold with Wilson intervals where
available, and the log-odds of every page and sentence. The Llama Prompt Guard 2 runs (86M and 22M,
2026-10-07) ran on Kaggle CPU kernels (x86) with the same `bench/baselines.py avaliar`; they also record the
kernel environment (`ambiente`), the label check (`checagem_rotulo`) and the latency of the proventra model
on the same VM (`ancora_latencia`), because their latency is not comparable with the ARM VM of the other runs. The 300-character README excerpts of the
"most suspicious benign pages" were removed from the public files (third-party text).

## `v6/`: v3 x v6 comparison / comparação v3 x v6

`v6.md` (write-up, in Portuguese), `v6.json` (numbers), `v6-tabelas.md` (tables) and `dados/` (per-item
P(injection) and gold labels for every test, per-page and per-window probabilities, nearest-neighbour
cosine of each Weni text). `v6.json` is reproducible from `dados/`:

```
PTGUARD_CACHE=results/v6/dados python analysis/comparar_versoes.py --base v3 --nova v6 \
  --res-base results/guard/v3-e5large-20261006.json,results/guard/v3-e5large-extras-20261006.json \
  --res-nova results/guard/v6-e5large-a-20261006.json,results/guard/v6-e5large-extras-20261006.json,results/guard/v6-e5large-b-20261006.json \
  --pag-base results/v6/dados/paginas-640-160-v3.json --pag-nova results/v6/dados/paginas-640-160-v6.json \
  --weni-vizinhos results/v6/dados/weni_vizinhos.json --saida work/v6-check
```

## `runs/` (ignored by git) / (fora do git)

Default output of new evaluations (`pipeline/treinar.py avaliar`, `sonda`); set `PTGUARD_RESULTADOS` to change it.
