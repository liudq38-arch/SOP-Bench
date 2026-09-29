#!/usr/bin/env bash
set -euo pipefail

MODEL=/data_1/ldq/models/Qwen3.8_27B
VLLM=/home/ldq/project/sop/.venv-impact/bin/vllm
OUT=/home/ldq/project/sop/outputs/impact_qa/qwen38_vllm
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export LD_PRELOAD=/home/ldq/miniconda3/envs/sop/lib/libstdc++.so.6
mkdir -p "$OUT"

start_service() {
  local devices="$1"
  local port="$2"
  local log="$OUT/qwen38_${port}.log"
  CUDA_VISIBLE_DEVICES="$devices" nohup "$VLLM" serve "$MODEL" \
    --host 127.0.0.1 \
    --port "$port" \
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
    --allowed-local-media-path /home/ldq/project/sop/outputs/impact_qa \
    >"$log" 2>&1 < /dev/null &
  SERVICE_PID="$!"
}

pids=()
start_service 0,1 8000
pids+=("$SERVICE_PID")
start_service 2,3 8001
pids+=("$SERVICE_PID")
printf '%s\n' "${pids[@]}"
wait "${pids[@]}"
