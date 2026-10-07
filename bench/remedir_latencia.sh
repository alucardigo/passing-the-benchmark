#!/bin/bash
# Remede a latência por janela (1 por chamada e lote de 16) com a máquina ociosa (4 threads).
#   bash bench/remedir_latencia.sh [PID_A_ESPERAR] > latencia.log 2>&1
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
if [ -n "${1:-}" ]; then
  while kill -0 "$1" 2>/dev/null; do sleep 20; done
fi
R=results/baselines/por-rodada
carga() { cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || echo "?"; }
echo "=== $(date -Is) carga: $(carga)"
arquivos=()
for f in laya-e5large-v3-640 protectai-v2-1300 proventra-mdeberta-1300 deepset-1300 protectai-v2-640 proventra-mdeberta-640; do
  [ -s "$R/$f.json" ] && arquivos+=("$R/$f.json")
done
PTGUARD_THREADS=4 TOKENIZERS_PARALLELISM=false "$PY" bench/baselines.py latencia "${arquivos[@]}"
echo "=== FIM $(date -Is) carga: $(carga)"
