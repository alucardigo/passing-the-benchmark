# Guard v3 x v3pub x v6

Gerado pelo script de comparação de três versões do estudo (`comparar_v3pub.py`, ainda não portado para este repositório) em 2026-10-07. Limiar 0,5 nos testes de frase; temperatura 1. Δ e McNemar exato pareado contra a v3.

## Testes de frase

| teste | o que mede | n | v3 | v3pub | v6 | Δ v3pub (p.p.) | McNemar p v3pub | Δ v6 (p.p.) | McNemar p v6 |
|---|---|---|---|---|---|---|---|---|---|
| weni | injeção pt-BR nativa (HackAPrompt traduzida), fora da distribuição | 300 | 94,7% | 68,0% | 63,7% | -26,67 | < 1e-6 | -31,0 | < 1e-6 |
| xtram1 | injeção/benigno en, fora da distribuição | 1500 | 98,7% | 95,4% | 99,3% | -3,27 | < 1e-6 | 0,67 | 0,031 |
| xtram1-pt | xTRam1 traduzido (Opus-MT) | 500 | 96,0% | 94,8% | 98,2% | -1,2 | 0,263 | 2,2 | 0,007 |
| massive_pt | benigno pt (comandos a assistente) | 1500 | 99,8% | 99,9% | 100,0% | 0,07 | 1,000 | 0,2 | 0,250 |
| dolly | benigno en (instruções a assistente) | 300 | 99,7% | 99,7% | 99,3% | 0,0 | 1,000 | -0,33 | 1,000 |
| dolly-pt | Dolly traduzido | 1000 | 99,3% | 99,8% | 99,6% | 0,5 | 0,062 | 0,3 | 0,250 |
| deepset | deepset en (teste oficial) | 116 | 94,8% | 94,0% | 88,8% | -0,86 | 1,000 | -6,03 | 0,016 |
| deepset-pt | deepset traduzido | 116 | 93,1% | 92,2% | 89,7% | -0,86 | 1,000 | -3,45 | 0,125 |
| jackhhao | jailbreak en (teste oficial) | 262 | 98,9% | 99,2% | 99,2% | 0,38 | 1,000 | 0,38 | 1,000 |
| jackhhao-pt | jackhhao traduzido | 262 | 98,1% | 98,9% | 98,5% | 0,76 | 0,688 | 0,38 | 1,000 |
| spml | SPML en (20% por hash) | 300 | 100,0% | 100,0% | 100,0% | 0,0 | 1,000 | 0,0 | 1,000 |
| spml-pt | SPML traduzido | 300 | 100,0% | 100,0% | 100,0% | 0,0 | 1,000 | 0,0 | 1,000 |
| so_perguntas | benigno técnico: perguntas do StackOverflow (20% por hash) | 300 | 33,3% | 41,0% | 100,0% | 7,67 | 0,002 | 66,67 | < 1e-6 |
| so_respostas | benigno técnico: respostas do StackOverflow (20% por hash) | 300 | 13,3% | 31,0% | 100,0% | 17,67 | < 1e-6 | 86,67 | < 1e-6 |
| docstrings | benigno técnico: docstrings Python (20% por hash) | 300 | 62,0% | 74,0% | 100,0% | 12,0 | 4,82e-06 | 38,0 | < 1e-6 |
| fumaca | fumaça pt-BR escrita à mão (10 frases) | 10 | 90,0% | 90,0% | 100,0% | 0,0 | 1,000 | 10,0 | 1,000 |

## Weni sem os itens contaminados na v3

58 dos 300 textos do Weni têm um vizinho (cosseno e5-base > 0,9) entre os 115 exemplos que só a v3 viu no treino.

| modelo | todos | contaminados | limpos | IC 95% (limpos) |
|---|---|---|---|---|
| v3 | 94,7% | 100,0% | 93,4% | 89,5%–95,9% |
| v3pub | 68,0% | 86,2% | 63,6% | 57,4%–69,4% |
| v6 | 63,7% | 75,9% | 60,7% | 54,5%–66,7% |

Pareado nos limpos (v3pub x v3): só a v3 acerta 73, só a v3pub acerta 1, McNemar p < 1e-6.

Pareado nos limpos (v6 x v3): só a v3 acerta 80, só a v6 acerta 1, McNemar p < 1e-6.

## Testes sem os itens que tinham duplicata no treino da v3

Itens de teste cujo texto (normalizado) aparece no treino da v3; a v3-pub não tem nenhum.

| teste | itens com duplicata | v3 com dup. | v3pub com dup. | v6 com dup. | v3 limpos | v3pub limpos | v6 limpos |
|---|---|---|---|---|---|---|---|
| jackhhao | 20 | 100,0% | 100,0% | 100,0% | 98,8% | 99,2% | 99,2% |
| spml | 15 | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% |
| xtram1 | 83 | 100,0% | 97,6% | 100,0% | 98,6% | 95,3% | 99,3% |
| massive_pt | 75 | 100,0% | 100,0% | 100,0% | 99,8% | 99,9% | 100,0% |
| dolly | 1 | 100,0% | 100,0% | 100,0% | 99,7% | 99,7% | 99,3% |
| jackhhao-pt | 6 | 100,0% | 100,0% | 100,0% | 98,0% | 98,8% | 98,4% |
| spml-pt | 1 | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% |
| xtram1-pt | 13 | 100,0% | 84,6% | 100,0% | 95,9% | 95,1% | 98,2% |

## Detecção x aviso falso, sem fixar limiar (frases)

Positivos de um teste contra negativos de outro; AUC e recall no limiar que segura o aviso falso em 2%.

| par | AUC v3 | AUC v3pub | AUC v6 | recall v3 @AF 2% | recall v3pub @AF 2% | recall v6 @AF 2% | AF v3 @0,5 | AF v3pub @0,5 | AF v6 @0,5 |
|---|---|---|---|---|---|---|---|---|---|
| weni_x_assistente | 0.999 | 0.9767 | 0.8833 | 100,0% | 95,7% | 77,0% | 0,4% | 0,2% | 0,2% |
| weni_x_tecnico | 0.8428 | 0.6547 | 0.8849 | 0,0% | 0,0% | 77,0% | 63,8% | 51,3% | 0,0% |
| xtram1-pt_x_assistente | 0.9993 | 0.979 | 0.9859 | 100,0% | 95,9% | 97,3% | 0,4% | 0,2% | 0,2% |
| xtram1-pt_x_tecnico | 0.893 | 0.8331 | 0.9864 | 0,0% | 0,0% | 97,3% | 63,8% | 51,3% | 0,0% |

## Página — janela 640/160 (a do hook)

| limiar | aviso falso v3 | aviso falso v3pub | aviso falso v6 | detecção v3 | detecção v3pub | detecção v6 |
|---|---|---|---|---|---|---|
| 0.5 | 100,0% | 100,0% | 34,6% | 100,0% | 100,0% | 90,0% |
| 0.9 | 100,0% | 100,0% | 30,4% | 100,0% | 100,0% | 85,0% |
| 0.95 | 100,0% | 100,0% | 29,0% | 100,0% | 100,0% | 85,0% |
| 0.99 | 100,0% | 100,0% | 24,0% | 100,0% | 100,0% | 83,3% |
| 0.999 | 100,0% | 100,0% | 19,4% | 100,0% | 100,0% | 81,7% |

AUC por página: v3 0.5046 · v3pub 0.5 · v6 0.8679.
Menor limiar com aviso falso ≤ 2%: v3 inalcançável · v3pub inalcançável · v6 inalcançável.
Janelas benignas com P ≥ 0,5: v3 99,6% · v3pub 98,6% · v6 7,2%.
Impressão das páginas: v3 349cf30a6cebfa99 · v3pub 349cf30a6cebfa99 · v6 349cf30a6cebfa99.
