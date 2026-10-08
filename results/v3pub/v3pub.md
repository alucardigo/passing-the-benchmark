# Guard v3-pub: pesos com licença limpa

> Relatório escrito durante o estudo (07/10/2026), em português. Os caminhos foram trocados pelos deste
> repositório e os comandos de infraestrutura privada saíram; os números são os originais. Duas correções:
> (1) na seção 2, a frase "todos os 300 textos do Weni têm vizinho acima de 0,85" contradiz a própria tabela
> por faixa; o mínimo é 0,826 e 271 de 300 ficam acima de 0,85. (2) No Resumo, "o xTRam1 agora é fora da
> distribuição de verdade" vai além dos dados: a v3-pub não tem as linhas do xTRam1 nem duplicatas dos 1.500
> itens de teste, mas 422 textos de treino dela (378 do jackhhao, 37 da Dolly) são iguais a textos do conjunto
> xTRam1 (`dados/auditoria.json`, chave `linhas_de_treino_iguais_a_algum_texto_do_xtram1_train_ou_test`). O
> artigo (seções 3.1, 4d e 7.2) incorpora este resultado com as ressalvas; o controle "v3 menos as 115" pedido
> na seção 3 ainda não foi rodado.

Rodada de 07/10/2026. Objeto: o classificador de prompt injection ("guard") deste estudo, e5-large ajustado, foco pt-BR.
A v3-pub é a versão que o plano de publicação do estudo recomenda publicar no lugar da v3.
Números brutos em `results/v3pub/v3pub.json`. As tabelas completas estão em `results/v3pub/v3pub-tabelas.md` e
saem do script de comparação de três versões do estudo (`comparar_v3pub.py`, ainda não portado para este
repositório; `analysis/comparar_versoes.py` compara duas versões).

## Resumo

A v3-pub usa a receita da v3 e um conjunto de treino que é um subconjunto estrito do da v3. Saem quatro grupos:

- as linhas do ShieldLM de origem `safeguard/*` (é o xTRam1, sem licença) e `trustailab/*` (licença divergente);
- todo texto de treino igual a um texto de teste;
- os pares de tradução desses textos;
- os quase-duplicados do Weni.

Resultado:

- **A licença e a contaminação ficam resolvidas.** Nenhum item de nenhum teste tem duplicata no treino. Antes eram
  20 no jackhhao, 83 no xTRam1, 439 no ShieldLM e 75 no MASSIVE. Os 109 textos (115 linhas) que a trava tirou da v6
  também não estão na v3-pub. Nenhum texto de treino coincide com os READMEs do teste de página.
- **A detecção em pt-BR cai tanto quanto na v6.** No Weni a v3-pub acerta 68,0%; a v3 acertava 94,7% e a v6 acerta
  63,7% (McNemar p < 1e-6 contra a v3). Nos 242 textos "limpos" do Weni o acerto cai de 93,4% para 63,6%.
- **O xTRam1 agora é fora da distribuição de verdade, e o número cai.** O acerto vai de 98,7% para 95,4% (p < 1e-6) e
  o recall de injeção fica em 90,3%. A v3 tinha visto o xTRam1 pelo ShieldLM (`safeguard/*`) e por 83 duplicatas.
- **O resto quase não muda.** deepset, jackhhao e SPML, em inglês e traduzidos, ficam dentro de ±1 p.p. (p ≥ 0,68).
  Os benignos de assistente ficam em 99,7% ou mais.
- **A página continua reprovada, igual à v3.** O aviso falso é de 100% em todo limiar de 0,5 a 0,999, e 98,6% das
  janelas benignas passam de 0,5. Em frase técnica benigna o aviso falso fica entre 26% e 69%.
- **Leitura:** a v3-pub não tem nenhum negativo técnico e perde no Weni quase o mesmo que a v6. Isso contradiz a
  leitura do `v6.md`, de que a perda no Weni vinha dos negativos técnicos ("atalho"). O que a v6 e a v3-pub têm em
  comum é ter tirado do treino exemplos próximos do Weni. A melhor hipótese agora é que o 94,7% da v3 dependia de
  vizinhos do teste bem mais do que o 1,3 p.p. estimado no `v6.md`. A atribuição fica para o controle "v3-limpa"
  (v3 − 115, sem nenhum outro corte), que roda em separado.

## 1. O que mudou no treino

| | v3 | v3-pub |
|---|---|---|
| exemplos | 23.693 | 21.935 |
| positivos (injeção) | 9.436 (39,8%) | 8.469 (38,6%) |
| relação | — | subconjunto estrito da v3: nenhum texto novo, 1.758 a menos |
| HackAPrompt, StackOverflow, docstrings | fora | fora |

Os quatro filtros foram aplicados em ordem pelo pipeline do estudo (`LAYA_PUB=1`). A rodada `v3-pub` de
`pipeline/treinar.py` ainda não os reproduz por inteiro: ela exclui só `safeguard/*` e não aplica a regra de pares
de tradução.

| filtro | regra | sai |
|---|---|---|
| origem excluída | linha do recorte de treino do ShieldLM com `source` em `safeguard/*` ou `trustailab/*` | 673 |
| duplicata de teste | texto igual a algum texto de qualquer teste, inclusive os traduzidos (espaços colapsados, caixa baixa) | 831 |
| par de tradução | se o original ou a tradução sai, o outro sai junto, até fechar | 164 |
| trava do Weni | cosseno e5-base > 0,9 com algum texto do Weni (a mesma trava da v6) | 90 |

Detalhes do que saiu:

- **O filtro de duplicatas vai além do pedido.** O plano de publicação pedia as 14 duplicatas do jackhhao. Com a regra
  normalizada, são 20 itens do teste jackhhao, e há duplicatas em quase todos os testes. Por isso o filtro foi
  generalizado para todos.
- **Os 831 removidos são, na maioria, positivos.** São 207 do SPML, 122 do jackhhao, 72 do ShieldLM, 61 do yanis e 15
  do deepset.
- **Os pares de tradução também são, na maioria, ataques traduzidos.** Saíram 86 do jackhhao-pt e 68 do SPML-pt.
- **A trava tirou só 90 linhas.** Contra 115 na v6, porque parte dos vizinhos do Weni já tinha saído nos filtros
  anteriores.

Composição por fonte e contagens por motivo e rótulo: `results/v3pub/dados/auditoria.json`. O arquivo só traz
contagens e índices de itens de teste.

Conferências feitas:

- Todo texto da v3-pub está na v3, idêntico.
- Dos 109 textos que só a v3 tinha em relação à v6, nenhum está na v3-pub.
- Nenhum item de teste tem duplicata normalizada no treino.
- Contra os 334 METADATA dos ambientes locais (superconjunto das 217 páginas; `analysis/checar_vazamento_paginas.py`):
  nenhum texto idêntico a um README, nenhum trecho de 200 caracteres ou mais em comum e nenhum 13-grama em comum
  (`dados/vazamento-paginas.json`).

O que não muda:

- **Receita.** O notebook `kaggle/guard-treino.ipynb` é o mesmo, sem alteração: `intfloat/multilingual-e5-large`, 3
  épocas, lr 2e-5, lote 8 × 4, aquecimento de 6%, fp16, `max_length` 256, prefixo `query: ` e validação interna de 8%
  estratificada. Rodou em Kaggle 2× T4 em 1 h 58 min. A validação interna deu 99,49% (v3: 99,63%; v6: 99,70%).
- **Dados no Kaggle.** O dataset de treino e o kernel são privados (`is_private=True`, conferido pela API); o dataset
  não é publicado porque contém texto de bases de terceiros.
- **Instalação.** Os pesos (ainda não publicados) ficaram em `models/prompt_injection-e5large-v3pub`, com temperatura
  1 e prefixo `query: `. O
  `config.json` é idêntico ao da v6. O sha256 de `model.safetensors` é
  `acb8d28f19b3613d8fe7ddf8c782993e5ef8cbf80830b455cbdbb45e7cf69769`, o mesmo na saída do Kaggle, na cópia local e na
  da VM ARM.
- **Avaliação.** Os testes, os textos, o código e a máquina são os da v3 e da v6: VM ARM na nuvem, CPU fp32, com o
  código de avaliação de md5 idêntico ao local. Os extras usam os mesmos 300 primeiros itens. A página usa as mesmas
  217 páginas benignas e 60 com injeção, com impressão `349cf30a6cebfa99`, pelo servidor de decisão do estudo (o caminho do hook).
- **Comparação.** É pareada contra a v3, com McNemar exato e intervalo de Wilson de 95%.

## 2. Resultados

Os testes de frase usam limiar 0,5 e temperatura 1. Δ = versão − v3, em pontos percentuais.

### Testes de frase

| teste | o que mede | n | v3 | v3-pub | v6 | Δ v3-pub | p v3-pub | Δ v6 | p v6 |
|---|---|---|---|---|---|---|---|---|---|
| weni | injeção pt-BR nativa, fora da distribuição | 300 | 94,7% | 68,0% | 63,7% | −26,7 | < 1e-6 | −31,0 | < 1e-6 |
| xtram1 | injeção/benigno en, fora da distribuição | 1500 | 98,7% | 95,4% | 99,3% | −3,3 | < 1e-6 | +0,7 | 0,031 |
| xtram1-pt | xTRam1 traduzido | 500 | 96,0% | 94,8% | 98,2% | −1,2 | 0,263 | +2,2 | 0,007 |
| massive_pt | benigno pt (comandos a assistente) | 1500 | 99,8% | 99,9% | 100,0% | +0,1 | 1,000 | +0,2 | 0,250 |
| dolly | benigno en | 300 | 99,7% | 99,7% | 99,3% | 0,0 | 1,000 | −0,3 | 1,000 |
| dolly-pt | Dolly traduzido | 1000 | 99,3% | 99,8% | 99,6% | +0,5 | 0,062 | +0,3 | 0,250 |
| deepset | deepset en (teste oficial) | 116 | 94,8% | 94,0% | 88,8% | −0,9 | 1,000 | −6,0 | 0,016 |
| deepset-pt | deepset traduzido | 116 | 93,1% | 92,2% | 89,7% | −0,9 | 1,000 | −3,5 | 0,125 |
| jackhhao | jailbreak en (teste oficial) | 262 | 98,9% | 99,2% | 99,2% | +0,4 | 1,000 | +0,4 | 1,000 |
| jackhhao-pt | jackhhao traduzido | 262 | 98,1% | 98,9% | 98,5% | +0,8 | 0,688 | +0,4 | 1,000 |
| spml | SPML en | 300 | 100,0% | 100,0% | 100,0% | 0,0 | 1,000 | 0,0 | 1,000 |
| spml-pt | SPML traduzido | 300 | 100,0% | 100,0% | 100,0% | 0,0 | 1,000 | 0,0 | 1,000 |
| so_perguntas | benigno técnico (StackOverflow) | 300 | 33,3% | 41,0% | 100,0% | +7,7 | 0,002 | +66,7 | < 1e-6 |
| so_respostas | benigno técnico (StackOverflow) | 300 | 13,3% | 31,0% | 100,0% | +17,7 | < 1e-6 | +86,7 | < 1e-6 |
| docstrings | benigno técnico (docstrings Python) | 300 | 62,0% | 74,0% | 100,0% | +12,0 | 4,8e-06 | +38,0 | < 1e-6 |
| fumaca | fumaça pt-BR escrita à mão | 10 | 90,0% | 90,0% | 100,0% | 0,0 | 1,000 | +10,0 | 1,000 |

No xTRam1 a v3-pub tem recall de 97,7% nos benignos e de 90,3% nas injeções. No xTRam1-pt os números são 97,5% e 88,4%.

### Weni sem os itens contaminados na v3

58 dos 300 textos do Weni têm um vizinho com cosseno e5-base > 0,9 entre os 115 exemplos que só a v3 viu no treino.

| modelo | todos | contaminados (58) | limpos (242) | IC 95% (limpos) |
|---|---|---|---|---|
| v3 | 94,7% | 100,0% | 93,4% | 89,5%–95,9% |
| v3-pub | 68,0% | 86,2% | 63,6% | 57,4%–69,4% |
| v6 | 63,7% | 75,9% | 60,7% | 54,5%–66,7% |

Pareado nos limpos (v3-pub × v3): só a v3 acerta 73 e só a v3-pub acerta 1 (McNemar p < 1e-6).

**O corte de 0,9 não separa limpo de contaminado tão bem quanto parecia.** O e5-base comprime os cossenos. Todos os
300 textos do Weni têm vizinho acima de 0,85 entre os 115, e os quantis de 10%, 50% e 90% ficam em 0,850, 0,887 e
0,906. Por faixa de similaridade:

| máx. cosseno aos 115 | n | v3 | v3-pub | v6 |
|---|---|---|---|---|
| (0,80; 0,85] | 29 | 100,0% | 6,9% | 69,0% |
| (0,85; 0,90] | 213 | 92,5% | 71,4% | 59,6% |
| (0,90; 1,00] | 58 | 100,0% | 86,2% | 75,9% |

A faixa menos parecida com os 115 é justamente onde a v3-pub mais erra (2 acertos em 29). Logo, o que a v3-pub perdeu
não se explica só pelos 115. Os outros cortes também tiraram ataques:

- 237 positivos do ShieldLM (`trustailab/*` e `safeguard/*`);
- 141 do jackhhao (duplicatas e origem);
- 207 do SPML;
- 168 ataques traduzidos (pares de tradução).

### Weni por limiar e troca detecção x aviso falso

| limiar | Weni v3 | Weni v3-pub | Weni v6 | AF assistente v3-pub (n = 2.800) | AF técnico v3-pub (n = 900) |
|---|---|---|---|---|---|
| 0,5 | 94,7% | 68,0% | 63,7% | 0,2% | 51,3% |
| 0,1 | 96,0% | 73,0% | 67,0% | 0,2% | 58,4% |
| 0,01 | 98,7% | 78,0% | 69,3% | 0,3% | 66,7% |
| 0,001 | 98,7% | 84,0% | 72,3% | 0,3% | 77,9% |

| par | AUC v3 | AUC v3-pub | AUC v6 | recall @AF 2% v3 | v3-pub | v6 |
|---|---|---|---|---|---|---|
| weni × assistente | 0,999 | 0,977 | 0,883 | 100,0% | 95,7% | 77,0% |
| weni × técnico | 0,843 | 0,655 | 0,885 | 0,0% | 0,0% | 77,0% |
| xtram1-pt × assistente | 0,999 | 0,979 | 0,986 | 100,0% | 95,9% | 97,3% |
| xtram1-pt × técnico | 0,893 | 0,833 | 0,986 | 0,0% | 0,0% | 97,3% |

Contra benignos de assistente, a v3-pub ainda ordena bem o Weni: AUC 0,977 e recall de 95,7% com aviso falso de 2%. O
erro dela no limiar 0,5 é mais de calibração do que de ordenação. A v6 é diferente: dá P = 0,0000 a 23% do Weni,
contra 4,3% na v3-pub. Contra benignos técnicos, nenhuma das duas versões sem negativos técnicos serve: a v3 e a
v3-pub têm recall de 0% com aviso falso de 2%.

### Página: janela 640/160 (a do hook)

| limiar | aviso falso v3 | aviso falso v3-pub | aviso falso v6 | detecção v3 | detecção v3-pub | detecção v6 |
|---|---|---|---|---|---|---|
| 0,5 | 100,0% | 100,0% | 34,6% | 100,0% | 100,0% | 90,0% |
| 0,9 | 100,0% | 100,0% | 30,4% | 100,0% | 100,0% | 85,0% |
| 0,95 | 100,0% | 100,0% | 29,0% | 100,0% | 100,0% | 85,0% |
| 0,99 | 100,0% | 100,0% | 24,0% | 100,0% | 100,0% | 83,3% |
| 0,999 | 100,0% | 100,0% | 19,4% | 100,0% | 100,0% | 81,7% |

- AUC por página: v3 0,505, v3-pub 0,500 e v6 0,868.
- Aviso falso ≤ 2%: inalcançável nas três versões.
- Janelas benignas com P ≥ 0,5: v3 99,6%, v3-pub 98,6% e v6 7,2%.

## 3. O que isto muda para a publicação

1. **A v3-pub é publicável quanto à licença:** MIT, sem linhas do xTRam1 e sem `trustailab`. Ela é também a única das
   três sem nenhuma duplicata de teste no treino. Os números honestos do model card passam a ser estes:
   - Weni 68,0% (63,6% nos limpos);
   - xTRam1 95,4%, agora de fato fora da distribuição;
   - página reprovada (217/217 avisos falsos).

   O 94,7% da v3 não pode aparecer como número dos pesos publicados.
2. **O artigo precisa ser corrigido em dois pontos.**
   - O número do Weni da v3 tinha vazamento por vizinhança muito maior que o 1,3 p.p. estimado. A v3-pub, sem os
     vizinhos e sem duplicatas, cai para 68,0%.
   - A explicação do `v6.md` para a queda da v6 no Weni ("os negativos técnicos tiraram o atalho") fica enfraquecida,
     porque a v3-pub cai quase o mesmo sem negativo técnico nenhum.

   A redação nova deve esperar o controle "v3-limpa", que separa o efeito dos 115 do efeito dos outros cortes.
3. **Nenhuma versão atende os dois critérios.** O critério de frase pede Weni ≥ 95% e a página pede aviso falso ≤ 2%. A v3-pub
   reprova nos dois. O hook continua desligado.

## 4. Problemas encontrados no caminho

1. **A sessão anterior parou por limite de sessão** depois do treino, da instalação e das duas avaliações. Esta sessão
   só recolheu os resultados da VM ARM, conferiu os hashes e gerou as tabelas. Nada foi re-treinado.
2. **Havia probabilidades locais parciais da v3-pub** (11:50, sete testes), de uma execução local interrompida. Elas foram descartadas e substituídas pelas da VM ARM, que são
   completas e vêm da mesma máquina da v3 e da v6.
3. **Memória local.** `checar_vazamento_paginas.py --base-antiga` deu `MemoryError`: o commit do Windows estava com
   2,3 GB livres. Por isso a auditoria de página rodou sem `--base-antiga`. A relação v3-pub ⊂ v3 foi conferida à
   parte, por conjunto.

## 5. Reprodução

```
# exportar: a rodada v3-pub deste repositório é uma aproximação (exclui só safeguard/*, sem a regra de pares de
# tradução); a exportação do estudo aplicou os quatro filtros da seção 1
python pipeline/treinar.py exportar --rodada v3-pub --saida work/v3pub
python pipeline/treinar.py exportar --rodada v3 --saida work/v3
python bench/paginas/construir.py
python analysis/checar_vazamento_paginas.py work/v3pub/treino.jsonl
# treinar (Kaggle, GPU 2x T4; dataset e kernel PRIVADOS: contêm texto de terceiros)
python kaggle/gerar_notebook.py
python kaggle/publicar.py dados --dataset ptguard-treino-v3pub --arquivo work/v3pub/treino.jsonl
python kaggle/publicar.py treinar --dataset ptguard-treino-v3pub --kernel ptguard-finetune
python kaggle/publicar.py baixar --kernel ptguard-finetune --saida work/v3pub/saida
# avaliar frases (os mesmos três blocos da v6; --max-teste 300 nos extras)
python pipeline/treinar.py avaliar models/prompt_injection-e5large-v3pub --testes weni,xtram1-pt,fumaca
python pipeline/treinar.py avaliar models/prompt_injection-e5large-v3pub --max-teste 300 \
  --testes deepset,deepset-pt,jackhhao,jackhhao-pt,spml,spml-pt,so_perguntas,so_respostas,docstrings,dolly
python pipeline/treinar.py avaliar models/prompt_injection-e5large-v3pub --testes xtram1,massive_pt,dolly-pt
# avaliar página (as mesmas 217 + 60 páginas)
python bench/paginas/avaliar.py models/prompt_injection-e5large-v3pub --janela 640 --sobra 160
```

Dados por item (públicos) em `results/v3pub/dados/`:

- `probs/v3pub/`: P(injeção) e gabarito de cada teste (os da v3 e da v6 estão em `results/v6/dados/probs/`);
- `paginas-640-160-v3pub.json`: pior janela por página e todas as janelas, só probabilidades;
- `auditoria.json` e `vazamento-paginas.json`;
- `extra.json`: receita, Kaggle, hashes e as análises de limiar e similaridade.

Os resultados brutos da avaliação por frase estão em `results/guard/v3pub-e5large-{a,extras,b}-20261007.json`
(mapa em `results/README.md`).
