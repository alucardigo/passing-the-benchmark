#!/bin/bash
# Roda a comparação de guards públicos no protocolo de página (a do artigo rodou numa VM ARM de 4 núcleos,
# Ampere A1, 24 GB). Antes: python bench/paginas/construir.py (monta work/paginas.json).
#   bash bench/rodar_baselines.sh [PID_A_ESPERAR] > baselines.log 2>&1
# Variáveis: PYTHON (padrão: python), E5 (pasta do nosso e5-large v3; padrão models/prompt_injection-e5large).
# Em máquina compartilhada, mede antes de cada rodada a CPU ocupada por outros processos e usa 2, 3 ou 4
# threads (thread a mais que núcleo livre faz o OpenMP esperar e fica MAIS lento).
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
export TOKENIZERS_PARALLELISM=false
R=results/baselines/por-rodada
mkdir -p "$R"

# rodada anterior ainda em curso: espera terminar
if [ -n "${1:-}" ]; then
  while kill -0 "$1" 2>/dev/null; do sleep 30; done
fi

threads() {
  local ocupado
  ocupado=$(top -b -n 2 -d 3 2>/dev/null | awk '/^top -/{n++} n==2 && $1 ~ /^[0-9]+$/ {s+=$9} END{printf "%d", s}')
  if [ "${ocupado:-0}" -gt 150 ]; then echo 2; elif [ "${ocupado:-0}" -gt 60 ]; then echo 3; else echo 4; fi
}

run() {
  local saida="${@: -1}" t
  if [ -s "$saida" ]; then echo "=== já existe: $saida"; return; fi
  t=$(threads)
  echo "=== $(date -Is) threads=$t $*"
  PTGUARD_THREADS=$t "$PY" bench/baselines.py avaliar "$@" || echo "FALHOU: $*"
}

E5="${E5:-models/prompt_injection-e5large}"
PA=protectai/deberta-v3-base-prompt-injection-v2
DS=deepset/deberta-v3-base-injection
PV=proventra/mdeberta-v3-base-prompt-injection

# Protocolo principal: janela = o que cabe no max_length de cada modelo
run "$PA" INJECTION --janela 1300 --sobra 200 --max-length 512 --nome protectai-v2 --saida "$R/protectai-v2-1300.json"
run "$DS" INJECTION --janela 1300 --sobra 200 --max-length 512 --nome deepset --saida "$R/deepset-1300.json"
run "$PV" INJECTION --janela 1300 --sobra 200 --max-length 512 --nome proventra-mdeberta --saida "$R/proventra-mdeberta-1300.json"
if [ -d "$E5" ]; then
  run "$E5" true --janela 640 --sobra 160 --max-length 256 --nome laya-e5large-v3 --saida "$R/laya-e5large-v3-640.json"
else
  echo "=== sem $E5: pulei o nosso e5-large v3"
fi

# Controle: a mesma janela 640/160 para todos (isola o efeito do tamanho da janela; só página).
# O deepset não entra: a saída dele já satura em 1300 e o controle não acrescenta informação.
run "$PA" INJECTION --janela 640 --sobra 160 --max-length 512 --sem-frases --nome protectai-v2 --saida "$R/protectai-v2-640.json"
run "$PV" INJECTION --janela 640 --sobra 160 --max-length 512 --sem-frases --nome proventra-mdeberta --saida "$R/proventra-mdeberta-640.json"

echo "=== FIM $(date -Is)"
