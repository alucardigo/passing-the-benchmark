# Third-party attributions and licenses

Code in this repository: **Apache-2.0** (`LICENSE`). Paper and results: **CC BY 4.0**
(`LICENSE-CC-BY-4.0.md`). Model weights: **MIT**, both the probe-B weights in `results/sonda-b/`
(`results/sonda-b/LICENSE`) and the fine-tuned weights, when published on the Hugging Face Hub.

**No third-party text is redistributed here.** Datasets and models are downloaded from their original
source at the revisions pinned in `ptguard/revisoes.json` (captured on 2026-10-06, after the training
runs of 2026-10-05/06, which did not pin revisions). The page benchmark ships only package names,
versions, file names and hashes; `bench/paginas/construir.py` downloads the text from PyPI.

This file is not legal advice. Where community practice and the letter of a license are not settled,
the position taken is stated explicitly.

## Base models and tools

| Model | Revision | License | Use |
|---|---|---|---|
| `intfloat/multilingual-e5-large` | `3d7cfbda` | MIT | base of the fine-tuned v3/v5/v6 classifiers. Wang et al., "Multilingual E5 Text Embeddings: A Technical Report", 2024 (arXiv:2402.05672). |
| `intfloat/multilingual-e5-base` | `d1287505` | MIT | frozen encoder of the probes; base of v2/v4. Same citation. |
| `Helsinki-NLP/opus-mt-tc-big-en-pt` | `9f2863d8` | CC-BY-4.0 | translation only (greedy, local); the model is not redistributed. Tiedemann & Thottingal, "OPUS-MT — Building open translation services for the World", EAMT 2020; Tiedemann, "The Tatoeba Translation Challenge", WMT 2020. The license of a translation follows its source text. |
| Laya (Convai Innovations, `convaiinnovations/laya`) | — | Apache-2.0 | integration context discussed in the paper; the classifiers do **not** derive from Laya weights, and this project is not affiliated with Convai. |

## Training data (revision · license · what was done)

- `deepset/prompt-injections` @`4f61ecb0` — Apache-2.0 — subsample; part translated to pt-BR (Opus-MT).
- `jackhhao/jailbreak-classification` @`2f2ceeb3` — Apache-2.0 (attacks from `verazuo/jailbreak_llms`,
  MIT; benign prompts from OpenOrca and GPTeacher) — part translated.
- `reshabhs/SPML_Chatbot_Prompt_Injection` @`02ce8084` — MIT — subsample of 4,000; part translated.
  Sharma et al., "SPML: A DSL for Defending Language Models Against Prompt Attacks", 2024
  (arXiv:2402.11755). Its card advises against training detectors on it; the paper lists this as a
  threat to validity.
- `rikka-snow/prompt-injection-multilingual` @`f1ad1f3d` — MIT.
- `dmilush/shieldlm-prompt-injection` @`dd660ae7` — MIT (curation); each source keeps its own license
  (alespalla/chatbot_instruction_prompts Apache-2.0, SPML, xTRam1, TrustAIRLab/in-the-wild-jailbreak-prompts
  [MIT at the source; the ShieldLM card says CC-BY-NC-SA-4.0], Harelix Apache-2.0, yanismiraoui
  Apache-2.0, deepset Apache-2.0, InjecAgent MIT, jackhhao, JailbreakBench MIT). Subsample of 4,000
  training rows, **577 of which come from the train split of xTRam1**, which declares no license (see
  below). The v3-pub round (trained 2026-10-07, `results/v3pub/`) removed them, together with the
  TrustAIRLab rows; `pipeline/treinar.py exportar --rodada v3-pub` drops the xTRam1 rows only.
- `yanismiraoui/prompt_injections` @`bd55359f` — Apache-2.0; its NOTICE is reproduced in `NOTICE` and
  below.
- AmazonScience/massive (via `mteb/amazon_massive_intent` @`940fd47a`, config `pt`) — CC-BY-4.0 at the
  origin (the mirror declares Apache-2.0). FitzGerald et al., "MASSIVE: A 1M-Example Multilingual Natural
  Language Understanding Dataset with 51 Typologically-Diverse Languages", ACL 2023 (arXiv:2204.08582).
  Subsample of 1,500. It is European Portuguese, not pt-BR.
- `databricks/databricks-dolly-15k` @`bdd27f4d` — CC-BY-SA-3.0, © Databricks; includes Wikipedia
  material (CC-BY-SA-3.0). Used as benign examples; part translated. Translations, if ever published,
  will be released under CC-BY-SA. Weights are released under MIT, the same position Databricks took for
  dolly-v2, which was trained on this dataset; weights are not treated as an "Adaptation".
- HackAPrompt (`hackaprompt/hackaprompt-dataset` @`25b87fbe`) — MIT. Schulhoff et al., "Ignore This Title
  and HackAPrompt: Exposing Systemic Vulnerabilities of LLMs Through a Global Prompt Hacking
  Competition", EMNLP 2023 (arXiv:2311.16119). Only successful attacks on gpt-3.5-turbo; rounds v4/v5 only
  (ablation). The runs reported in the paper read the mirror `imoxto/prompt_injection_hackaprompt_gpt35`
  @`efc8f438`, which declares no license; this code reads the MIT origin instead.
- Stack Overflow — user contributions under CC-BY-SA (2.5/3.0/4.0 depending on the post date), via
  `pacovaldez/stackoverflow-questions` @`869802e5` and `koutch/stackoverflow_python` @`ee6f3955`. Benign
  technical examples, round v6 only; not translated; text not redistributed.
- CodeSearchNet (via `Nan-Do/code-search-net-python` @`39db9186`) — each example keeps the license of its
  source repository (only repositories whose license allows redistribution were kept). Husain et al.,
  "CodeSearchNet Challenge: Evaluating the State of Semantic Code Search", 2019 (arXiv:1909.09436). Round v6 only.

## Evaluation only (never redistributed, never translated in public)

- `Weni/prompt-injections-1.0.0` @`9707fa47` — no license declared. Native pt-BR test set; the training
  pipeline removes near-duplicates of it (cosine > 0.9) from rounds v4–v6.
- `xTRam1/safe-guard-prompt-injection` @`a3a877d6` — no license declared. English test set (and, through
  ShieldLM, 577 training rows: it is the same distribution, not out-of-distribution).
- Page benchmark: long descriptions (README) of 217 PyPI packages, each under the license of its package.
  This repository ships only name, version, file name and SHA-256; the builder downloads them from PyPI.

## Baselines (only numbers are published)

| Model | Revision | License |
|---|---|---|
| `protectai/deberta-v3-base-prompt-injection-v2` | `90c9989b` | Apache-2.0 |
| `proventra/mdeberta-v3-base-prompt-injection` | `b8a89d30` | MIT (as recorded from its model card on 2026-10-06) |
| `deepset/deberta-v3-base-injection` | `80dda00d` | MIT |
| `meta-llama/Llama-Prompt-Guard-2-86M` | `a8ded8e6` | Llama 4 Community License; gated. Evaluated on 2026-10-07 after the license was accepted; only numbers are published and the weights are not redistributed. Its outputs are not used to train, calibrate or distill any model of this project. |
| `meta-llama/Llama-Prompt-Guard-2-22M` | `11614a15` | Llama 4 Community License; gated. Same as above. |
| `meta-llama/Prompt-Guard-86M` | — | Llama 3.1 Community License; gated. Not evaluated (access not granted, HTTP 403 on 2026-10-07). |

## Python packages

All permissive; no obligation beyond keeping their notices: `transformers`, `datasets`, `huggingface_hub`
(Apache-2.0), `scikit-learn`, `numpy` (BSD-3-Clause), `torch` (BSD-style), `sentencepiece` (Apache-2.0),
`kaggle` (Apache-2.0).

## NOTICE of yanismiraoui/prompt_injections

```
prompt_injections dataset
Copyright 2023 Yanis Miraoui

Licensed under the Apache License, Version 2.0 (the "License");
you may not use the contents of this repository except in compliance
with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This NOTICE applies to the dataset contents (including prompt_injections.csv)
as well as the accompanying documentation in this repository.
```
