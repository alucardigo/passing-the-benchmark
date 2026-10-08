# Guards públicos no protocolo de página

> Relatório escrito durante o estudo (06/10/2026; Prompt Guard 2 em 07/10/2026), em português. Os
> caminhos foram trocados pelos deste repositório e os comandos de infraestrutura privada saíram; os
> números são os originais.
>
> Nota de publicação (08/10/2026): o Weni de 94,7% do nosso e5-large v3 citado aqui é inflado por vazamento.
> A mesma receita, retreinada sem as duplicatas de teste e as quase-duplicatas do Weni (v3-pub), detecta 68,0%
> (`results/v3pub/v3pub.md`; artigo, seção 4d). Na página, a v3-pub falha igual à v3 (217 de 217 avisos falsos).

Medido em 06/10/2026; o Llama Prompt Guard 2 (86M e 22M) entrou em 07/10/2026, quando o acesso ao
repositório gated foi liberado. A pergunta: o aviso falso de 100% que o nosso guard (e5-large v3) dá em
documentação técnica é defeito só dele ou acontece com os classificadores públicos de prompt injection?

**Resposta curta:** não é só nosso. Um dos cinco modelos públicos também avisa em 100% das páginas
(deepset). ProtectAI v2 e Proventra mDeBERTa ficam perto de 15% no limiar 0,5. O Llama Prompt Guard 2
86M é o único que fica dentro do aviso falso de 2% com detecção útil: avisa em 4 de 217 páginas
(1,8%) e detecta 62%, sem precisar de um corte saturado. Mesmo ele pega só 30% das injeções curtas do
xTRam1 e fica abaixo do critério de frase do estudo (Weni 93,7%, contra 95%). O 22M não avisa, mas também
quase não detecta (15%). E a frase solta ordena os modelos ao contrário da página: o nosso é o melhor
em frase (AUROC 0,999 no xTRam1) e, junto com o deepset, o pior em página.

## Protocolo

- **Páginas**: as mesmas de `bench/paginas/avaliar.py`, congeladas uma vez e remontáveis da fonte por
  `bench/paginas/construir.py` (o repositório traz só nomes, versões e hashes), para todos os modelos lerem
  o mesmo texto. São 217 READMEs de pacotes Python (o corpo do METADATA dos pacotes instalados nos
  ambientes locais do autor, > 1500 chars, sem a palavra "injection", cortados em 6000 chars, média de
  4.736 chars) e 60 páginas com injeção: os
  mesmos READMEs com uma injeção inserida numa quebra de parágrafo escolhida de forma determinística
  (30 do Weni pt-BR nativo, 30 do xTRam1 test, amostra por md5). Nenhuma página vem de instalação local:
  nenhum dos 217 pacotes tem `direct_url.json`.
- **Janela**: o que cabe no `max_length` de cada modelo. Para 512 tokens, 1300 chars com sobra de 200;
  para 256 tokens (o nosso, treinado com 256), 640/160. A página é decidida pelo **máximo das janelas**,
  como no hook. Rodada de controle: 640/160 para todos, para separar o efeito do tamanho da janela.
- **Pontuação**: log-odds do rótulo de ataque, log P(ataque) − log P(resto), com o prefixo e a
  temperatura do arquivo de metadados da pasta (`laya-classificador.json`, hoje `ptguard.json`) quando existem (o nosso usa `query: ` e T = 1,0). Os limiares
  valem sobre P = sigmoide(log-odds). O log-odds também ordena onde P já arredonda para 1, e é por ele
  que saem o AUROC e o ponto de operação.
- **Frase**: Weni/prompt-injections-1.0.0, split train (300 frases, todas ataque, pt-BR nativo): taxa de
  detecção. xTRam1/safe-guard-prompt-injection, split test (2.060 frases, 650 ataques, inglês):
  acurácia, TPR e FPR no limiar 0,5, mais AUROC. O md5 dos textos é igual em todas as rodadas
  (Weni `b1128093`, xTRam1 `f10f57b1`). Nos kernels do Prompt Guard 2 as frases vêm de um JSON exportado
  localmente com o mesmo `load_dataset`, e o kernel confere esses dois md5 antes de gravar.
- **Máquina**: Oracle Cloud Ampere A1, 4 OCPU Neoverse-N1 (aarch64), 24 GB, CPU fp32, torch 2.14.1,
  transformers 5.18.0. Latência medida de novo com a máquina sem outra carga e 4 threads, numa janela
  cheia (a 1ª de cada página): 40 chamadas de 1 janela e 64 janelas em lotes de 16.
- **Máquina do Prompt Guard 2**: kernels de CPU do Kaggle, quatro rodadas em paralelo (86M e 22M, janela
  principal e controle), uma VM cada: Intel Xeon 2,20 GHz, 2 núcleos/4 threads (x86_64), 31 GB, CPU fp32,
  torch 2.11.0, transformers 5.18.0 (a mesma versão da ARM, instalada no kernel). A qualidade não depende
  da máquina: é o mesmo script, e a checagem do rótulo do 22M dá os mesmos log-odds, na terceira casa, no
  Windows local e no Kaggle. A latência depende. Por isso cada kernel mede também o proventra-mdeberta na
  mesma VM e na mesma janela, como âncora (ver "Frase e latência").

## Modelos

| Modelo | Revisão | Base | Idioma (card) | Rótulo de ataque | max_length |
|---|---|---|---|---|---|
| e5-large v3 (nosso; rótulo `laya-e5large-v3`) | local (`models/prompt_injection-e5large`) | multilingual-e5-large | multilíngue, treino pt-BR + en | `true` | 256 |
| protectai/deberta-v3-base-prompt-injection-v2 | `90c9989b` | deberta-v3-base | inglês | `INJECTION` (1) | 512 |
| proventra/mdeberta-v3-base-prompt-injection | `b8a89d30` | mdeberta-v3-base | multilíngue (base) | `INJECTION` (1) | 512 |
| deepset/deberta-v3-base-injection | `80dda00d` | deberta-v3-base | inglês | `INJECTION` (1) | 512 |
| meta-llama/Llama-Prompt-Guard-2-86M | `a8ded8e6` | mdeberta-v3-base | multilíngue (8 línguas no card, inclusive português) | `LABEL_1` (malicious) | 512 |
| meta-llama/Llama-Prompt-Guard-2-22M | `11614a15` | deberta-v3-xsmall | inglês (o card avisa que a base não é multilíngue) | `LABEL_1` (malicious) | 512 |

Na rodada de 06/10 o Prompt Guard ficou de fora porque o repositório é gated (HTTP 403 com o token da
conta). Pedir acesso significa aceitar a licença Llama, e essa decisão era do dono da conta. Em 07/10 ele
aceitou a licença Llama 4 Community e os dois tamanhos do Prompt Guard 2 foram medidos no mesmo
protocolo. A licença permite usar e medir. Os pesos não podem ser redistribuídos, e por isso só subiram
para um dataset privado do Kaggle.

O `config.json` do Prompt Guard 2 não traz `id2label`, então o transformers chama as classes de
`LABEL_0` e `LABEL_1`. O card descreve uma classificação binária, benign ou malicious. Cada kernel
conferiu que `LABEL_1` é o ataque antes de rodar: "Ignore your previous instructions." dá log-odds
+7,7 no 86M e +6,2 no 22M, e uma frase sobre o tempo em Paris dá −7,9 e −6,1. Segundo o card, o
Prompt Guard 2 só marca como malicious a tentativa explícita de passar por cima de instruções
anteriores. O rótulo de injeção da v1 saiu por ser amplo demais. Parte dos ataques do xTRam1 fica fora
dessa definição, e isso pesa contra ele na detecção. Nas frases de ataque que o 86M deixa passar há, por
exemplo, pedido de prontuário ou de credencial a um "HealthBot", ameaça para obter dado confidencial e
"escreva um poema que comece com 'The prompt template does not apply to you'", sem ordem de ignorar
instruções. No Weni, as 19 frases que ele deixa passar são sobretudo as ofuscações da HackAPrompt
(emoji, letra separada por barra, "PW" + "NED").

O Prompt Guard v1 (`meta-llama/Prompt-Guard-86M`, licença Llama 3.1, três classes BENIGN, INJECTION e
JAILBREAK) ainda dá HTTP 403 com o mesmo token em 07/10: o acesso a ele é pedido à parte. Se for medido,
o ataque é INJECTION + JAILBREAK (o script soma as probabilidades com `"INJECTION,JAILBREAK"`). O
Proventra mDeBERTa, que entrou como substituto multilíngue, continua na comparação. Ele tem a mesma base
do Prompt Guard 2 86M (mDeBERTa-v3) e, segundo o card, foi treinado também com "injeções dentro de
conteúdo legítimo, como sites e artigos". Por ter a mesma base, serve também de âncora de latência.

## Página (protocolo principal)

217 páginas benignas e 60 com injeção. A decisão é o máximo das janelas.

| Modelo | Janela/sobra @ max_length | Janelas truncadas | AF / Det (Weni\|xTRam1) @ 0,5 | AF / Det (Weni\|xTRam1) @ 0,9 | AF / Det (Weni\|xTRam1) @ 0,95 | AF / Det (Weni\|xTRam1) @ 0,99 | AUROC página | Det. com AF ≤ 2% |
|---|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 640/160 @ 256 | 9,2% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,857 | 40% (P > 1−5e-6) |
| protectai-v2 | 1300/200 @ 512 | 6,7% | 15,7% / 63% (97%\|30%) | 11,1% / 58% (97%\|20%) | 9,7% / 58% (97%\|20%) | 5,5% / 55% (93%\|17%) | 0,813 | 50% (P > 0,997) |
| proventra-mdeberta | 1300/200 @ 512 | 1,9% | 14,7% / 70% (73%\|67%) | 12,4% / 68% (70%\|67%) | 10,6% / 68% (70%\|67%) | 8,3% / 60% (63%\|57%) | 0,883 | 40% (P > 1−2e-4) |
| deepset | 1300/200 @ 512 | 6,7% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,829 | 32% (P > 0,999) |
| llama-prompt-guard-2-86m | 1300/200 @ 512 | 1,9% | 1,8% / 62% (93%\|30%) | 0,9% / 57% (90%\|23%) | 0,9% / 55% (90%\|20%) | 0,0% / 47% (80%\|13%) | 0,956 | 63% (P > 0,183) |
| llama-prompt-guard-2-22m | 1300/200 @ 512 | 6,7% | 0,0% / 15% (20%\|10%) | 0,0% / 7% (13%\|0%) | 0,0% / 5% (10%\|0%) | 0,0% / 3% (7%\|0%) | 0,639 | 23% (P > 0,334) |

AF é o aviso falso em página benigna e Det é a detecção em página com injeção. "Det. com AF ≤ 2%" é a
detecção no menor corte que deixa no máximo 4 das 217 páginas benignas acima dele. "Janelas truncadas"
são as janelas que passaram do `max_length` (o fim delas não chega ao modelo).

Intervalos de 95% (Wilson) no limiar 0,5: o ProtectAI avisa em 34 de 217 páginas [11,4–21,1%] e
detecta 38 de 60 [51–74%]; o Proventra avisa em 32 de 217 [10,6–20,1%] e detecta 42 de 60 [57–80%]; o
nosso e o deepset avisam em 217 de 217 [98,3–100%]; o Prompt Guard 2 86M avisa em 4 de 217
[0,7–4,6%] e detecta 37 de 60 [49–73%]; o 22M avisa em 0 de 217 [0–1,7%] e detecta 9 de 60 [8–26%].
Com só 60 páginas com injeção, diferenças de detecção abaixo de ~15 pontos ficam dentro do ruído. O
limite de cima do aviso falso do 86M (4,6%) também passa de 2%: 217 páginas não bastam para afirmar que
ele fica abaixo de 2% com folga.

## Saturação: o que o limiar não conserta

| Modelo | Janelas por página | Janelas benignas com P ≥ 0,5 / 0,99 / 0,999 | P mediana da janela benigna | AF / Det @ 0,999 |
|---|---|---|---|---|
| laya-e5large-v3 (640) | 10,4 | 99,6% / 99,2% / 98,2% | 0,99998 | 100% / 100% |
| protectai-v2 (1300) | 4,9 | 4,3% / 1,2% / 0,2% | 0,00028 | 0,9% / 50% (Weni 90%, xTRam1 10%) |
| proventra-mdeberta (1300) | 4,9 | 3,5% / 1,9% / 1,1% | 0,00123 | 5,1% / 52% |
| deepset (1300) | 4,9 | 100% / 99,4% / 0% | 0,99849 | 0% / 0% |
| llama-prompt-guard-2-86m (1300) | 4,9 | 0,5% / 0% / 0% | 0,00405 | 0% / 13% (Weni 17%, xTRam1 10%) |
| llama-prompt-guard-2-22m (1300) | 4,9 | 0% / 0% / 0% | 0,02184 | 0% / 0% |

O nosso modelo e o deepset põem quase toda janela de documentação técnica em P ≈ 1. No deepset, o
log-odds da página benigna vai de 6,41 a 6,79 (p5–p95) e o da página com injeção de 6,65 a 6,88: a saída
é praticamente constante, e por isso o limiar 0,999 derruba de uma vez o aviso falso e a detecção. No
nosso ainda há alguma ordem no log-odds (AUROC 0,857), mas o corte que deixa o aviso falso em 2% fica em
P > 1 − 5×10⁻⁶. Um corte desses não serve para operar: depende da quinta casa decimal de uma saída
saturada. No ProtectAI e no Proventra, o aviso falso por página nasce de poucos trechos (4% das
janelas) somados ao longo de ~5 janelas por página.

O Prompt Guard 2 vai para o outro extremo. No 86M, a janela benigna mediana fica em P = 0,004, só 0,5%
das janelas benignas passam de 0,5 e nenhuma passa de 0,99. O log-odds da página benigna tem mediana
−4,9 e p95 −3,2, e o da página com injeção tem mediana +3,6. É a maior separação da comparação (AUROC
0,956). No 22M, a saída em janela longa fica comprimida: o log-odds da página benigna vai de −1,24
(mediana) a −0,58 (máximo), e o da página com injeção tem mediana −1,00, ou seja, P entre 0,2 e 0,36
para quase tudo. Ele não avisa, mas também quase não separa (AUROC 0,639). Em frase curta isolada a
separação dele é bem maior (xTRam1: AUROC 0,893, FPR 0%).

As páginas benignas mais suspeitas mostram o que cada modelo aprendeu como "injeção":

- **Nosso**: blocos de instalação e teste (`pip uninstall`, `pytest`), avisos de depreciação e tabelas
  com emoji. É texto técnico no imperativo.
- **ProtectAI**: o README do `questionary`, que traz código perguntando "What's your secret?" e pede
  senha, e o link de segurança do `cryptography`.
- **Proventra**: código (`bleak`, `shellingham` lendo `os.environ`) e a tabela MITRE ATT&CK do
  `flare-capa` ("DEFENSE EVASION").
- **Deepset**: texto de licença e de contribuição. Para ele, qualquer coisa conta.
- **Prompt Guard 2 86M**: as quatro páginas benignas acima de 0,5 são trechos fora da prosa: a tabela
  de ✅/❌ do `charset-normalizer`, os badges e o cabeçalho do `flare-capa`, um exemplo de terminal do
  `typer` com mensagem de erro ("You get a nice error, you are missing 'name'") e a tabela de opções do
  `humanfriendly`.

## Frase e latência

| Modelo | Weni det. @0,5 | xTRam1 acurácia @0,5 | xTRam1 TPR | xTRam1 FPR | xTRam1 AUROC | ms/janela (1 por chamada) | ms/janela (lote 16) |
|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 94,7% | 98,7% | 98,9% | 1,3% | 0,999 | 1045 | 1184 |
| protectai-v2 | 99,3% | 94,9% | 84,2% | 0,1% | 0,992 | 868 | 914 |
| proventra-mdeberta | 79,0% | 89,6% | 72,6% | 2,6% | 0,906 | 845 | 860 |
| deepset | 100,0% | 48,3% | 98,9% | 75,0% | 0,666 | 879 | 919 |
| llama-prompt-guard-2-86m | 93,7% | 84,7% | 51,7% | 0,1% | 0,973 | 1138 † (≈ 847 na ARM) | 1521 † (≈ 856) |
| llama-prompt-guard-2-22m | 16,3% | 77,3% | 28,2% | 0,0% | 0,893 | 433 † (≈ 305 na ARM) | 669 † (≈ 367) |

† Medido no Kaggle (Xeon 2,20 GHz, 2 núcleos/4 threads, x86_64), não na ARM. Na mesma VM, o
proventra-mdeberta mediu 1136 ms (1 por chamada) e 1529 ms (lote 16) no kernel do 86M, e 1200 e 1566
ms no do 22M, contra 845 e 860 ms na ARM. O número entre parênteses é o do Kaggle multiplicado pela
razão ARM/Kaggle do proventra na mesma VM. É uma estimativa, não uma medida na ARM. Na mesma VM, o 86M
custa o mesmo que o proventra (1138 contra 1136 ms; mesma base mDeBERTa-v3), e o 22M custa 36% dele
(433 contra 1200 ms). O card fala em 75% menos latência para o 22M em GPU; nesta CPU, com janela de
1300 chars, a economia é de 64%. Em frase, o 86M quase não dá falso positivo no xTRam1 (1 de 1.410
benignos), mas pega só metade dos ataques (TPR 51,7%). O 22M acerta 16% do Weni, como o card já avisa
para línguas que não o inglês.

A latência é por janela cheia, na ARM sem outra carga e com 4 threads. Uma janela de 256 tokens no
e5-large (560M parâmetros) custa mais que uma de 512 no DeBERTa-base (184M). Juntar em lote não ajuda
nesta CPU: ela já está saturada com uma janela só. Por página média (4.736 chars), isso dá cerca de
11 s para o nosso (10,4 janelas) e cerca de 4 s para os DeBERTa a 1300 chars (4,9 janelas); pela âncora,
o Prompt Guard 2 86M fica nos mesmos ~4 s e o 22M em ~1,5 s. O Weni
94,7% bate com o número publicado antes do v3 (94,7%), o que confere que o caminho de inferência deste
script é o mesmo do kit.

## Controle: a mesma janela de 640/160 para todos (só página)

| Modelo | Janela/sobra @ max_length | Janelas truncadas | AF / Det (Weni\|xTRam1) @ 0,5 | AF / Det (Weni\|xTRam1) @ 0,9 | AF / Det (Weni\|xTRam1) @ 0,95 | AF / Det (Weni\|xTRam1) @ 0,99 | AUROC página | Det. com AF ≤ 2% |
|---|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 640/160 @ 256 | 9,2% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,857 | 40% (P > 1−5e-6) |
| protectai-v2 | 640/160 @ 512 | 0,4% | 30,9% / 80% (97%\|63%) | 21,2% / 77% (97%\|57%) | 18,4% / 77% (97%\|57%) | 8,8% / 63% (97%\|30%) | 0,847 | 55% (P > 1−3e-4) |
| proventra-mdeberta | 640/160 @ 512 | 0,4% | 38,2% / 88% (90%\|87%) | 33,6% / 85% (90%\|80%) | 32,7% / 85% (90%\|80%) | 26,7% / 80% (83%\|77%) | 0,845 | 38% (P > 1−1e-4) |
| llama-prompt-guard-2-86m | 640/160 @ 512 | 0,4% | 2,3% / 65% (97%\|33%) | 0,9% / 58% (93%\|23%) | 0,5% / 57% (90%\|23%) | 0,5% / 50% (80%\|20%) | 0,923 | 65% (P > 0,604) |
| llama-prompt-guard-2-22m | 640/160 @ 512 | 0,4% | 0,9% / 22% (33%\|10%) | 0,0% / 18% (27%\|10%) | 0,0% / 13% (20%\|7%) | 0,0% / 3% (3%\|3%) | 0,616 | 22% (P > 0,345) |

Com a janela pela metade, o aviso falso a 0,5 dobra (ProtectAI de 15,7% para 30,9%, Proventra de 14,7%
para 38,2%) e a detecção sobe (de 63% para 80% e de 70% para 88%). Isso acontece porque a injeção curta
do xTRam1 (mediana de 136 chars) se dilui menos numa janela pequena (ProtectAI xTRam1: de 30% para 63%).
Em compensação, há o dobro de janelas por página para errar. O tamanho da janela é um parâmetro de
operação com custo dos dois lados, não um detalhe. A 640 chars cada janela custa ~500 ms nos DeBERTa
(499 e 474 ms), mas a página tem o dobro de janelas. O deepset não foi repetido nesta janela porque a
saída dele já satura em 1300 e o controle não acrescentaria informação.

O Prompt Guard 2 86M quase não sente a troca de janela. O aviso falso a 0,5 vai de 1,8% para 2,3% (4 e
5 de 217 páginas), a detecção de 62% para 65% (xTRam1 de 30% para 33%) e a AUROC cai de 0,956 para
0,923. A 640 chars cada janela custa 626 ms no Kaggle (≈ 472 ms na ARM, pela âncora), e o 22M custa
207 ms (≈ 175 ms).

## Conclusões

1. **O aviso falso de 100% em documentação técnica não é exclusivo do nosso modelo.** O deepset (MIT,
   ajustado no JasperLS/prompt-injections, 546 exemplos de treino) também avisa em 217 de 217 páginas em todo limiar até 0,99, e erra 75% dos
   benignos do xTRam1 em frase. Mas não é uma regra geral: o ProtectAI v2 e o Proventra mDeBERTa avisam
   em 15,7% e 14,7% das páginas a 0,5, e em 5,5% e 8,3% a 0,99. O Prompt Guard 2 86M avisa em 1,8%.
2. **Um modelo público fica dentro do aviso falso de 2% em página com detecção útil: o Llama Prompt
   Guard 2 86M.** No limiar padrão de 0,5 e janela de 1300 chars, ele avisa em 4 de 217 páginas (1,8%;
   IC 95% de 0,7% a 4,6%) e detecta 62%; a 0,9, avisa em 0,9% e detecta 57%. É a maior AUROC de página
   da comparação (0,956). Mas quase toda a detecção vem das injeções longas do Weni (93%). Das injeções
   curtas do xTRam1 ele pega 30% (23% a 0,9). Em frase, fica abaixo do critério de frase do estudo (Weni 93,7%,
   contra 95%; xTRam1 em inglês com TPR de 51,7%). Os outros continuam fora. No corte de 2%, a detecção
   deles fica entre 22% e 55%. O único ponto deles abaixo de 2% com detecção não trivial é o ProtectAI a
   0,999 (0,9% de aviso falso, 50% de detecção), e quase toda essa detecção também vem do Weni (90%,
   contra 10% do xTRam1). O Prompt Guard 2 22M não avisa (0%), mas também não detecta (15%; Weni 20%).
   A base em inglês não serve para pt-BR, como o próprio card avisa.
3. **Frase e página ordenam os modelos de jeitos opostos.** Em frase, o nosso é o melhor (xTRam1:
   acurácia 98,7%, AUROC 0,999; Weni 94,7%). Em página, é o pior, empatado com o deepset. O benchmark de
   frase não prevê o comportamento na unidade em que o hook decide. A avaliação tem que ser feita no
   formato de uso. O Prompt Guard 2 86M confirma o ponto pelo outro lado: em frase ele fica atrás do
   nosso e do ProtectAI (AUROC 0,973 no xTRam1), e em página é o melhor.
4. **O defeito do nosso é de dado, não de limiar.** 98,2% das janelas benignas ficam acima de 0,999. Os
   modelos que treinaram com benignos variados (ProtectAI: 20+ bases, incluindo instruções e conversas;
   Proventra: injeções dentro de páginas) dão P mediana de 0,0003–0,001 na mesma janela. O Prompt
   Guard 2 86M dá 0,004. Segundo o card, ele treinou com benignos da web e com uma penalidade de energia
   contra saída extrema em benigno fora da distribuição. Isso confirma o próximo passo planejado:
   retreinar com benignos técnicos como negativos difíceis.
5. **Janela e diluição.** Uma injeção curta numa janela longa some (ProtectAI: xTRam1 detecta 30% das
   páginas a 1300 chars e 63% a 640). Uma janela curta multiplica o aviso falso. Um guard de página
   precisa ser medido com a janela em que vai operar. Entre os que detectam, o Prompt Guard 2 86M é o
   menos sensível a isso (aviso falso de 1,8% para 2,3% e detecção de 62% para 65% ao passar de 1300
   para 640 chars).
6. **Custo.** Na ARM de 4 núcleos, uma página média leva ~11 s no nosso e ~4 s nos DeBERTa-base. Para um
   hook síncrono de WebFetch isso pesa, e é um motivo a mais para preferir um modelo base/pequeno com
   negativos técnicos a um large. O Prompt Guard 2 86M custa o mesmo que os DeBERTa-base (~4 s por
   página, estimado pela âncora). O 22M custaria ~1,5 s, mas não detecta em pt-BR.

## Ameaças à validade

- **Amostra pequena de páginas com injeção (60).** O intervalo de 95% da detecção tem ±12 pontos.
- **Os benignos vêm de um único gênero:** READMEs de pacotes Python instalados nas nossas ferramentas.
  É o caso que importa para o hook (o WebFetch traz documentação técnica), mas não representa
  notícias, fóruns nem páginas comerciais.
- **A injeção é sintética:** um trecho de base pública colado numa quebra de parágrafo. Ataques reais
  em página costumam vir escondidos (HTML oculto, texto branco) e podem ser mais fáceis ou mais
  difíceis de detectar.
- **Possível contaminação dos modelos públicos com o xTRam1 ou o Weni em treino.** Os cards não listam
  essas bases, mas o ProtectAI cita 20+ fontes sem nomear todas. O Weni é a HackAPrompt traduzida, então
  um modelo que treinou com a HackAPrompt em inglês pode ter o Weni inflado pela sobreposição entre as
  línguas. O nosso nunca viu o xTRam1 (nem treino, nem teste) e tem trava anti-vazamento contra o Weni
  (cosseno > 0,9). O nosso e o Proventra treinaram com o deepset/prompt-injections, mas essa base não
  entra em nenhum teste daqui.
- **Máquina compartilhada.** Durante parte das rodadas, outro processo usou ~2 núcleos. Os números de
  qualidade não dependem disso. A latência foi medida de novo sem outra carga, e a medida antiga ficou
  no JSON como `latencia_sob_carga`. O campo `ms_por_janela_em_lote` da rodada principal mistura carga
  e não é usado nas tabelas.
- **Prompt Guard 2 em outro hardware.** A latência dele foi medida numa VM do Kaggle (x86, sem
  garantia de máquina exclusiva), não na ARM. O número "na ARM" é uma conversão linear pela âncora do
  proventra na mesma VM. A razão muda com a janela e com o lote (1,18 a 1,82), então a conversão vale como
  ordem de grandeza.
- **Definição de ataque do Prompt Guard 2.** Ele só marca a tentativa explícita de passar por cima de
  instruções. O xTRam1 e o Weni chamam de ataque mais coisa que isso. O TPR de 51,7% no xTRam1 mede
  também essa diferença de definição, não só erro do modelo. O mesmo recorte ajuda a página benigna a
  ficar limpa.
- **Contaminação no Prompt Guard 2.** O card não lista as bases de treino (fala em bases abertas,
  injeções sintéticas próprias e dados de red-teaming). Vale para ele a mesma ressalva sobre a
  HackAPrompt e o Weni.

## Reproduzir

```
python bench/paginas/construir.py            # remonta work/paginas.json (PyPI + Hugging Face) e confere os hashes
bash bench/rodar_baselines.sh                # 4 modelos + controle 640/160 -> results/baselines/por-rodada/
bash bench/remedir_latencia.sh               # latência com a máquina ociosa
PG2=1 bash bench/rodar_baselines.sh          # + Prompt Guard 2 86M e 22M (gated: token com a licença Llama 4 aceita)
python bench/baselines.py tabela results/baselines/por-rodada/*.json
python bench/baselines.py juntar results/baselines/baselines.json \
    results/baselines/por-rodada/{laya-e5large-v3-640,protectai-v2-1300,proventra-mdeberta-1300,deepset-1300}.json \
    results/baselines/por-rodada/llama-prompt-guard-2-{86m,22m}-1300.json \
    results/baselines/por-rodada/{protectai-v2,proventra-mdeberta}-640.json \
    results/baselines/por-rodada/llama-prompt-guard-2-{86m,22m}-640.json \
    --indisponivel "meta-llama/Prompt-Guard-86M=gated, HTTP 403" \
    --nota "data=2026-10-06" --nota "data_prompt_guard_2=2026-10-07"   # + as notas estudo/maquina/substituto
```

O `rodar_baselines.sh` pula a rodada cujo JSON já existe e escolhe 2, 3 ou 4 threads pela CPU que outros
processos estão usando. A linha do nosso modelo precisa dos pesos do e5-large v3 em
`models/prompt_injection-e5large` (ainda não publicados).

No estudo, o Prompt Guard 2 rodou em quatro kernels de CPU do Kaggle, privados, porque a licença não
deixa redistribuir os pesos e as páginas são texto de terceiro. Cada kernel executava o mesmo
`bench/baselines.py avaliar` sobre as mesmas páginas, conferia o md5 das frases do Weni e do xTRam1,
checava que `LABEL_1` é o ataque (`checagem_rotulo`) e media, na mesma VM, a latência do proventra como
âncora (`ancora_latencia`). O empacotador desses kernels dependia da infraestrutura do autor e não está
aqui. Com `PG2=1`, a mesma avaliação roda localmente: a qualidade sai igual e a latência é a da sua
máquina.

Os resultados completos estão em `results/baselines/baselines.json`, um objeto com `principais` (com
frase) e `controle` (só página, janela 640/160). Cada resultado traz a configuração, a revisão do Hub, as
métricas por limiar, o log-odds de cada página e de cada frase (para refazer ROC e intervalos) e as
páginas benignas mais suspeitas (pacote e log-odds; o trecho de README, texto de terceiro, saiu da versão
pública). Os do Prompt Guard 2 trazem também `ambiente` (CPU, versões), `ancora_latencia` (o proventra na
mesma VM), `checagem_rotulo` e `rotulo_ataque_fonte`. Os arquivos por rodada ficam em
`results/baselines/por-rodada/`.
