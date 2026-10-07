# Guards públicos no protocolo de página

> Relatório escrito durante o estudo (06/10/2026), em português. Os caminhos foram trocados pelos deste
> repositório e os comandos de infraestrutura privada saíram; os números são os originais.

Medido em 06/10/2026. A pergunta: o aviso falso de 100% que o nosso guard (e5-large v3) dá em
documentação técnica é defeito só dele ou acontece com os classificadores públicos de prompt injection?

**Resposta curta:** não é só nosso. Um dos três modelos públicos também avisa em 100% das páginas
(deepset). Os dois mais cuidados (ProtectAI v2 e Proventra mDeBERTa) ficam perto de 15% no limiar 0,5,
mas nenhum chega ao critério de ligar o hook (aviso falso ≤ 2% com detecção útil). E a frase solta
ordena os modelos ao contrário da página: o nosso é o melhor em frase (AUROC 0,999 no xTRam1) e, junto
com o deepset, o pior em página.

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
  (Weni `b1128093`, xTRam1 `f10f57b1`).
- **Máquina**: Oracle Cloud Ampere A1, 4 OCPU Neoverse-N1 (aarch64), 24 GB, CPU fp32, torch 2.14.1,
  transformers 5.18.0. Latência medida de novo com a máquina sem outra carga e 4 threads, numa janela
  cheia (a 1ª de cada página): 40 chamadas de 1 janela e 64 janelas em lotes de 16.

## Modelos

| Modelo | Revisão | Base | Idioma (card) | Rótulo de ataque | max_length |
|---|---|---|---|---|---|
| e5-large v3 (nosso; rótulo `laya-e5large-v3`) | local (`models/prompt_injection-e5large`) | multilingual-e5-large | multilíngue, treino pt-BR + en | `true` | 256 |
| protectai/deberta-v3-base-prompt-injection-v2 | `90c9989b` | deberta-v3-base | inglês | `INJECTION` (1) | 512 |
| proventra/mdeberta-v3-base-prompt-injection | `b8a89d30` | mdeberta-v3-base | multilíngue (base) | `INJECTION` (1) | 512 |
| deepset/deberta-v3-base-injection | `80dda00d` | deberta-v3-base | inglês | `INJECTION` (1) | 512 |

Ficaram de fora porque o acesso foi negado (repositório gated, HTTP 403 com o token da conta):
`meta-llama/Llama-Prompt-Guard-2-86M` e `meta-llama/Prompt-Guard-86M`. Pedir acesso significa aceitar a
licença Llama, e essa decisão é do dono da conta, não minha. O Proventra mDeBERTa entra no lugar como
representante multilíngue: tem a mesma base do Prompt Guard (mDeBERTa-v3) e, segundo o card, foi
treinado também com "injeções dentro de conteúdo legítimo, como sites e artigos".

## Página (protocolo principal)

217 páginas benignas e 60 com injeção. A decisão é o máximo das janelas.

| Modelo | Janela/sobra @ max_length | Janelas truncadas | AF / Det (Weni\|xTRam1) @ 0,5 | AF / Det (Weni\|xTRam1) @ 0,9 | AF / Det (Weni\|xTRam1) @ 0,95 | AF / Det (Weni\|xTRam1) @ 0,99 | AUROC página | Det. com AF ≤ 2% |
|---|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 640/160 @ 256 | 9,2% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,857 | 40% (P > 1−5e-6) |
| protectai-v2 | 1300/200 @ 512 | 6,7% | 15,7% / 63% (97%\|30%) | 11,1% / 58% (97%\|20%) | 9,7% / 58% (97%\|20%) | 5,5% / 55% (93%\|17%) | 0,813 | 50% (P > 0,997) |
| proventra-mdeberta | 1300/200 @ 512 | 1,9% | 14,7% / 70% (73%\|67%) | 12,4% / 68% (70%\|67%) | 10,6% / 68% (70%\|67%) | 8,3% / 60% (63%\|57%) | 0,883 | 40% (P > 1−2e-4) |
| deepset | 1300/200 @ 512 | 6,7% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,829 | 32% (P > 0,999) |

AF é o aviso falso em página benigna e Det é a detecção em página com injeção. "Det. com AF ≤ 2%" é a
detecção no menor corte que deixa no máximo 4 das 217 páginas benignas acima dele. "Janelas truncadas"
são as janelas que passaram do `max_length` (o fim delas não chega ao modelo).

Intervalos de 95% (Wilson) no limiar 0,5: o ProtectAI avisa em 34 de 217 páginas [11,4–21,1%] e
detecta 38 de 60 [51–74%]; o Proventra avisa em 32 de 217 [10,6–20,1%] e detecta 42 de 60 [57–80%]; o
nosso e o deepset avisam em 217 de 217 [98,3–100%]. Com só 60 páginas com injeção, diferenças de
detecção abaixo de ~15 pontos ficam dentro do ruído.

## Saturação: o que o limiar não conserta

| Modelo | Janelas por página | Janelas benignas com P ≥ 0,5 / 0,99 / 0,999 | P mediana da janela benigna | AF / Det @ 0,999 |
|---|---|---|---|---|
| laya-e5large-v3 (640) | 10,4 | 99,6% / 99,2% / 98,2% | 0,99998 | 100% / 100% |
| protectai-v2 (1300) | 4,9 | 4,3% / 1,2% / 0,2% | 0,00028 | 0,9% / 50% (Weni 90%, xTRam1 10%) |
| proventra-mdeberta (1300) | 4,9 | 3,5% / 1,9% / 1,1% | 0,00123 | 5,1% / 52% |
| deepset (1300) | 4,9 | 100% / 99,4% / 0% | 0,99849 | 0% / 0% |

O nosso modelo e o deepset põem quase toda janela de documentação técnica em P ≈ 1. No deepset, o
log-odds da página benigna vai de 6,41 a 6,79 (p5–p95) e o da página com injeção de 6,65 a 6,88: a saída
é praticamente constante, e por isso o limiar 0,999 derruba de uma vez o aviso falso e a detecção. No
nosso ainda há alguma ordem no log-odds (AUROC 0,857), mas o corte que deixa o aviso falso em 2% fica em
P > 1 − 5×10⁻⁶. Um corte desses não serve para operar: depende da quinta casa decimal de uma saída
saturada. Nos dois modelos bons, o aviso falso por página nasce de poucos trechos (4% das janelas)
somados ao longo de ~5 janelas por página.

As páginas benignas mais suspeitas mostram o que cada modelo aprendeu como "injeção":

- **Nosso**: blocos de instalação e teste (`pip uninstall`, `pytest`), avisos de depreciação e tabelas
  com emoji. É texto técnico no imperativo.
- **ProtectAI**: o README do `questionary`, que traz código perguntando "What's your secret?" e pede
  senha, e o link de segurança do `cryptography`.
- **Proventra**: código (`bleak`, `shellingham` lendo `os.environ`) e a tabela MITRE ATT&CK do
  `flare-capa` ("DEFENSE EVASION").
- **Deepset**: texto de licença e de contribuição. Para ele, qualquer coisa conta.

## Frase e latência

| Modelo | Weni det. @0,5 | xTRam1 acurácia @0,5 | xTRam1 TPR | xTRam1 FPR | xTRam1 AUROC | ms/janela (1 por chamada) | ms/janela (lote 16) |
|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 94,7% | 98,7% | 98,9% | 1,3% | 0,999 | 1045 | 1184 |
| protectai-v2 | 99,3% | 94,9% | 84,2% | 0,1% | 0,992 | 868 | 914 |
| proventra-mdeberta | 79,0% | 89,6% | 72,6% | 2,6% | 0,906 | 845 | 860 |
| deepset | 100,0% | 48,3% | 98,9% | 75,0% | 0,666 | 879 | 919 |

A latência é por janela cheia, na ARM sem outra carga e com 4 threads. Uma janela de 256 tokens no
e5-large (560M parâmetros) custa mais que uma de 512 no DeBERTa-base (184M). Juntar em lote não ajuda
nesta CPU: ela já está saturada com uma janela só. Por página média (4.736 chars), isso dá cerca de
11 s para o nosso (10,4 janelas) e cerca de 4 s para os DeBERTa a 1300 chars (4,9 janelas). O Weni
94,7% bate com o número publicado antes do v3 (94,7%), o que confere que o caminho de inferência deste
script é o mesmo do kit.

## Controle: a mesma janela de 640/160 para todos (só página)

| Modelo | Janela/sobra @ max_length | Janelas truncadas | AF / Det (Weni\|xTRam1) @ 0,5 | AF / Det (Weni\|xTRam1) @ 0,9 | AF / Det (Weni\|xTRam1) @ 0,95 | AF / Det (Weni\|xTRam1) @ 0,99 | AUROC página | Det. com AF ≤ 2% |
|---|---|---|---|---|---|---|---|---|
| laya-e5large-v3 | 640/160 @ 256 | 9,2% | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 100,0% / 100% (100%\|100%) | 0,857 | 40% (P > 1−5e-6) |
| protectai-v2 | 640/160 @ 512 | 0,4% | 30,9% / 80% (97%\|63%) | 21,2% / 77% (97%\|57%) | 18,4% / 77% (97%\|57%) | 8,8% / 63% (97%\|30%) | 0,847 | 55% (P > 1−3e-4) |
| proventra-mdeberta | 640/160 @ 512 | 0,4% | 38,2% / 88% (90%\|87%) | 33,6% / 85% (90%\|80%) | 32,7% / 85% (90%\|80%) | 26,7% / 80% (83%\|77%) | 0,845 | 38% (P > 1−1e-4) |

Com a janela pela metade, o aviso falso a 0,5 dobra (ProtectAI de 15,7% para 30,9%, Proventra de 14,7%
para 38,2%) e a detecção sobe (de 63% para 80% e de 70% para 88%). Isso acontece porque a injeção curta
do xTRam1 (mediana de 136 chars) se dilui menos numa janela pequena (ProtectAI xTRam1: de 30% para 63%).
Em compensação, há o dobro de janelas por página para errar. O tamanho da janela é um parâmetro de
operação com custo dos dois lados, não um detalhe. A 640 chars cada janela custa ~500 ms nos DeBERTa
(499 e 474 ms), mas a página tem o dobro de janelas. O deepset não foi repetido nesta janela porque a
saída dele já satura em 1300 e o controle não acrescentaria informação.

## Conclusões

1. **O aviso falso de 100% em documentação técnica não é exclusivo do nosso modelo.** O deepset (MIT,
   ajustado no JasperLS/prompt-injections, 546 exemplos de treino) também avisa em 217 de 217 páginas em todo limiar até 0,99, e erra 75% dos
   benignos do xTRam1 em frase. Mas não é uma regra geral: o ProtectAI v2 e o Proventra mDeBERTa avisam
   em 15,7% e 14,7% das páginas a 0,5, e em 5,5% e 8,3% a 0,99.
2. **Nenhum modelo público passa no critério de ligar o hook** (aviso falso ≤ 2% em página com
   detecção útil). No corte de 2%, a detecção fica entre 32% e 55%. O único ponto abaixo de 2% com
   detecção não trivial é o ProtectAI a 0,999 (0,9% de aviso falso, 50% de detecção), e quase toda essa
   detecção vem das injeções longas do Weni (90%, contra 10% do xTRam1).
3. **Frase e página ordenam os modelos de jeitos opostos.** Em frase, o nosso é o melhor (xTRam1:
   acurácia 98,7%, AUROC 0,999; Weni 94,7%). Em página, é o pior, empatado com o deepset. O benchmark de
   frase não prevê o comportamento na unidade em que o hook decide. A avaliação tem que ser feita no
   formato de uso.
4. **O defeito do nosso é de dado, não de limiar.** 98,2% das janelas benignas ficam acima de 0,999. Os
   modelos que treinaram com benignos variados (ProtectAI: 20+ bases, incluindo instruções e conversas;
   Proventra: injeções dentro de páginas) dão P mediana de 0,0003–0,001 na mesma janela. Isso confirma
   o próximo passo planejado: retreinar com benignos técnicos como negativos difíceis.
5. **Janela e diluição.** Uma injeção curta numa janela longa some (ProtectAI: xTRam1 detecta 30% das
   páginas a 1300 chars e 63% a 640). Uma janela curta multiplica o aviso falso. Um guard de página
   precisa ser medido com a janela em que vai operar.
6. **Custo.** Na ARM de 4 núcleos, uma página média leva ~11 s no nosso e ~4 s nos DeBERTa-base. Para um
   hook síncrono de WebFetch isso pesa, e é um motivo a mais para preferir um modelo base/pequeno com
   negativos técnicos a um large.

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

## Reproduzir

```
python bench/paginas/construir.py            # remonta work/paginas.json (PyPI + Hugging Face) e confere os hashes
bash bench/rodar_baselines.sh                # 4 modelos + controle 640/160 -> results/baselines/por-rodada/
bash bench/remedir_latencia.sh               # latência com a máquina ociosa
python bench/baselines.py tabela results/baselines/por-rodada/*.json
python bench/baselines.py juntar results/baselines/baselines.json results/baselines/por-rodada/*.json \
    --indisponivel "meta-llama/Llama-Prompt-Guard-2-86M=gated, HTTP 403" --nota "data=2026-10-06"
```

O `rodar_baselines.sh` pula a rodada cujo JSON já existe e escolhe 2, 3 ou 4 threads pela CPU que outros
processos estão usando. A linha do nosso modelo precisa dos pesos do e5-large v3 em
`models/prompt_injection-e5large` (ainda não publicados).

Os resultados completos estão em `results/baselines/baselines.json`, um objeto com `principais` (com
frase) e `controle` (só página, janela 640/160). Cada resultado traz a configuração, a revisão do Hub, as métricas por limiar, o
log-odds de cada página e de cada frase (para refazer ROC e intervalos) e as páginas benignas mais
suspeitas (pacote e log-odds; o trecho de README, texto de terceiro, saiu da versão pública). Os arquivos por rodada ficam em `results/baselines/por-rodada/`.
