#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 GPU_IDS PORT" >&2
  exit 2
fi

DEVICES="$1"
PORT="$2"
MODEL=/data_1/ldq/models/Qwen3.8_27B
VLLM=/home/ldq/project/sop/.venv-impact/bin/vllm
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export LD_PRELOAD=/home/ldq/miniconda3/envs/sop/lib/libstdc++.so.6

exec env CUDA_VISIBLE_DEVICES="$DEVICES" "$VLLM" serve "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --served-model-name impact-qwen38-27b \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 32768 \
  --max-num-seqs 8 \
  --gpu-memory-utilization 0.85 \
  --limit-mm-per-prompt '{"image":32,"video":1}' \
  --reasoning-parser qwen3 \
  --compilation-config '{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,2,4,8]}' \
  --disable-custom-all-reduce \
  --allowed-local-media-path /home/ldq/project/sop/outputs/impact_qa
