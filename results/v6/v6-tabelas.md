# Guard v6 (correção com benignos técnicos) x v3

Gerado por `analysis/comparar_versoes.py` em 2026-10-06. Limiar 0,5 nos testes de frase; temperatura 1.

## Testes de frase

| teste | o que mede | n | v3 | v6 | Δ (p.p.) | McNemar p |
|---|---|---|---|---|---|---|
| weni | injeção pt-BR nativa (HackAPrompt traduzida), fora da distribuição | 300 | 94,7% | 63,7% | -31,0 | < 1e-6 |
| xtram1 | injeção/benigno en, fora da distribuição | 1500 | 98,7% | 99,3% | 0,67 | 0,031 |
| xtram1-pt | xTRam1 traduzido (Opus-MT) | 500 | 96,0% | 98,2% | 2,2 | 0,007 |
| massive_pt | benigno pt (comandos a assistente) | 1500 | 99,8% | 100,0% | 0,2 | 0,250 |
| dolly | benigno en (instruções a assistente) | 300 | 99,7% | 99,3% | -0,33 | 1,000 |
| dolly-pt | Dolly traduzido | 1000 | 99,3% | 99,6% | 0,3 | 0,250 |
| deepset | deepset en (teste oficial) | 116 | 94,8% | 88,8% | -6,03 | 0,016 |
| deepset-pt | deepset traduzido | 116 | 93,1% | 89,7% | -3,45 | 0,125 |
| jackhhao | jailbreak en (teste oficial) | 262 | 98,9% | 99,2% | 0,38 | 1,000 |
| jackhhao-pt | jackhhao traduzido | 262 | 98,1% | 98,5% | 0,38 | 1,000 |
| spml | SPML en (20% por hash) | 300 | 100,0% | 100,0% | 0,0 | 1,000 |
| spml-pt | SPML traduzido | 300 | 100,0% | 100,0% | 0,0 | 1,000 |
| so_perguntas | benigno técnico: perguntas do StackOverflow (20% por hash) | 300 | 33,3% | 100,0% | 66,67 | < 1e-6 |
| so_respostas | benigno técnico: respostas do StackOverflow (20% por hash) | 300 | 13,3% | 100,0% | 86,67 | < 1e-6 |
| docstrings | benigno técnico: docstrings Python (20% por hash) | 300 | 62,0% | 100,0% | 38,0 | < 1e-6 |
| fumaca | fumaça pt-BR escrita à mão (10 frases) | 10 | 90,0% | 100,0% | 10,0 | 1,000 |

## Weni sem os itens contaminados na v3

58 dos 300 textos do Weni têm um vizinho (cosseno e5-base > 0,9) entre os exemplos que só a v3 viu no treino.

| modelo | contaminados | limpos | IC 95% (limpos) |
|---|---|---|---|
| v3 | 100,0% | 93,4% | 89,5%–95,9% |
| v6 | 75,9% | 60,7% | 54,5%–66,7% |

Pareado nos limpos: só a v3 acerta 80, só a v6 acerta 1, McNemar p < 1e-6.

## Detecção x aviso falso, sem fixar limiar (frases)

Positivos de um teste contra negativos de outro; AUC e recall no limiar que segura o aviso falso em 2% / 5%.
Probabilidades gravadas com 4 casas (empates em 0 e 1 limitam a resolução).

| par | AUC v3 | AUC v6 | recall v3 @AF 2% | recall v6 @AF 2% | recall v3 @AF 5% | recall v6 @AF 5% | AF v3 @0,5 | AF v6 @0,5 |
|---|---|---|---|---|---|---|---|---|
| weni_x_assistente | 0.999 | 0.8833 | 100,0% | 77,0% | 100,0% | 77,0% | 0,4% | 0,2% |
| weni_x_tecnico | 0.8428 | 0.8849 | 0,0% | 77,0% | 0,0% | 77,0% | 63,8% | 0,0% |
| xtram1-pt_x_assistente | 0.9993 | 0.9859 | 100,0% | 97,3% | 100,0% | 97,3% | 0,4% | 0,2% |
| xtram1-pt_x_tecnico | 0.893 | 0.9864 | 0,0% | 97,3% | 0,0% | 97,3% | 63,8% | 0,0% |

## Página — janela 640/160 (a do hook)

| limiar | aviso falso v3 | aviso falso v6 | detecção v3 | detecção v6 | det. Weni v6 | det. xTRam1 v6 |
|---|---|---|---|---|---|---|
| 0.5 | 100,0% | 34,6% | 100,0% | 90,0% | 90,0% | 90,0% |
| 0.9 | 100,0% | 30,4% | 100,0% | 85,0% | 86,7% | 83,3% |
| 0.95 | 100,0% | 29,0% | 100,0% | 85,0% | 86,7% | 83,3% |
| 0.99 | 100,0% | 24,0% | 100,0% | 83,3% | 86,7% | 80,0% |
| 0.999 | 100,0% | 19,4% | 100,0% | 81,7% | 83,3% | 80,0% |

AUC por página: v3 0.5046 · v6 0.8679.
Menor limiar com aviso falso ≤ 2%: v3 inalcançável (exigiria limiar > 1) · v6 inalcançável (exigiria limiar > 1).
Janelas benignas com P ≥ 0,5: v3 99,6% · v6 7,2%. Impressão das páginas: v3 349cf30a6cebfa99 · v6 349cf30a6cebfa99.
