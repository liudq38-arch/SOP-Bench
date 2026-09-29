import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, ROOT, read_jsonl
from impact_qa.tool_batch import parents, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['development', 'exposed_regression'])
    args = parser.parse_args()
    cases = read_jsonl(OUT / 'gt_v15_endpoint_inputs' / args.phase / 'contracts.jsonl')
    source = [ROOT / p for p in ['scripts/run_impact_tool_endpoints.py', 'scripts/prepare_impact_tool_endpoints.py', 'impact_qa/tool_batch.py', 'impact_qa/tool_review_v15.py', 'impact_qa/reliable_pool.py', 'impact_qa/api.py']]
    asyncio.run(run(cases, OUT / 'gt_v15_tools/endpoint8' / args.phase, parents(args.phase), ROOT / 'prompts/impact_qa/v15/tool_transition.txt', source, 'endpoint8', args.phase))
