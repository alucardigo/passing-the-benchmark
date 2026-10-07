# Paper / Artigo

**Passing the Benchmark, Failing the README: A Negative Result on Deploying a Brazilian Portuguese
Prompt-Injection Classifier**, Rodrigo Faria (Independent Researcher), 2026. CC BY 4.0.

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
