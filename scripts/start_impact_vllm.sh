set -euo pipefail
cd /home/ldq/project/sop
export CUDA_VISIBLE_DEVICES="${IMPACT_GPU_IDS:-0,1}"
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export LD_PRELOAD=/home/ldq/miniconda3/envs/sop/lib/libstdc++.so.6
exec .venv-impact/bin/vllm serve /data_1/ldq/models/Qwen3.5-27B --host 127.0.0.1 --port "${IMPACT_API_PORT:-8000}" --served-model-name impact-qwen35-27b --tensor-parallel-size 2 --dtype bfloat16 --max-model-len 32768 --max-num-seqs 4 --gpu-memory-utilization 0.85 --limit-mm-per-prompt '{"image":32,"video":1}' --reasoning-parser qwen3 --compilation-config '{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,2,4]}' --disable-custom-all-reduce --allowed-local-media-path /home/ldq/project/sop/outputs/impact_qa
