import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ROOT, REPORTS, save_json


def existing_service(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models', timeout=3) as response:
            models = json.load(response)
        if 'impact-qwen35-27b' not in [m['id'] for m in models['data']]:
            raise RuntimeError(f'service_manager: port {port} belongs to another model')
        return True
    except urllib.error.URLError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--services', type=int, default=4)
    args = parser.parse_args()
    if args.services < 1:
        raise ValueError('service_manager: services must be positive')
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.used', '--format=csv,noheader,nounits'], text=True)
    cards = [(int(line.split(',')[0]), int(line.split(',')[1])) for line in raw.splitlines()]
    count = min(args.services, len(cards) // 2)
    if not count:
        raise RuntimeError('service_manager: fewer than two visible GPUs')
    services = []
    for i in range(count):
        assigned = cards[2 * i:2 * i + 2]
        port = 8000 + i
        row = {'port': port, 'base_url': f'http://127.0.0.1:{port}/v1', 'gpu_ids': [g[0] for g in assigned], 'tensor_parallel_size': 2, 'max_num_seqs': 4, 'client_concurrency': 4}
        if existing_service(port):
            row['state'] = 'reused_healthy'
        else:
            if any(used > 1000 for _, used in assigned):
                raise RuntimeError(f'service_manager: GPUs {assigned} occupied without expected service on {port}')
            env = os.environ.copy()
            env.update(IMPACT_GPU_IDS=','.join(str(g[0]) for g in assigned), IMPACT_API_PORT=str(port))
            log_path = REPORTS / f'vllm_service_{port}.log'
            with log_path.open('a') as log:
                child = subprocess.Popen(['bash', str(ROOT / 'scripts/start_impact_vllm.sh')], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            row.update(state='starting', pid=child.pid, log=str(log_path))
        services.append(row)
    report = {'requested_services': args.services, 'visible_gpu_count': len(cards), 'launched_or_reused_services': count, 'total_client_concurrency': count * 4, 'services': services, 'limitation': 'Fourth TP2 service requires an eighth visible GPU.' if count < args.services else None}
    save_json(REPORTS / 'service_pool.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
