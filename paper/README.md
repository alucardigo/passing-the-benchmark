# Paper / Artigo

**Passing the Benchmark, Failing the README: Leakage and Shortcut Learning in a Brazilian Portuguese
Prompt-Injection Classifier**, Rodrigo Faria (Independent Researcher), 2026. CC BY 4.0.

Revised on 2026-10-07 (evening): a decontaminated retraining (v3-pub) showed that the best model's 94.7% on
the native pt-BR test was inflated by leakage (68.0% without it); title, abstract, Sections 3.4, 4, 7 and
9–13 and Table 5 were updated. Earlier versions are in the git history.

| | English | Português |
|---|---|---|
| PDF | [`passing-the-benchmark-en.pdf`](passing-the-benchmark-en.pdf) | [`passing-the-benchmark-pt.pdf`](passing-the-benchmark-pt.pdf) |
| LaTeX | [`en/main.tex`](en/main.tex) | [`pt/main.tex`](pt/main.tex) |

The English version is the one submitted to arXiv. Each `main.tex` is self-contained (preamble and body
inlined, comments removed) and compiles with pdfLaTeX; the bibliography is pre-built in `main.bbl`, so
BibTeX is optional (`refs.bib` is here for reuse):

```
cd paper/en && pdflatex main && pdflatex main
```

O PDF em português é a mesma versão do artigo; a submissão ao arXiv usa o inglês.
