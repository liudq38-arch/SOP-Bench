set -euo pipefail
cd /home/ldq/project/sop
export CUDA_VISIBLE_DEVICES=6
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export LD_PRELOAD=/home/ldq/miniconda3/envs/sop/lib/libstdc++.so.6
exec .venv-impact/bin/vllm serve /data_1/ldq/models/Qwen3-VL-8B-Instruct --host 127.0.0.1 --port 8003 --served-model-name impact-qwen3vl8b --tensor-parallel-size 1 --dtype bfloat16 --max-model-len 32768 --max-num-seqs 2 --gpu-memory-utilization 0.8 --limit-mm-per-prompt '{"image":32,"video":1}' --enforce-eager --allowed-local-media-path /home/ldq/project/sop/outputs/impact_qa
