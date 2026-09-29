import argparse
import asyncio
import fcntl
import os
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPACT_V26_CONFIG'] = 'configs/impact_qa/component_v27_video_gt_r6.json'
sys.path.insert(0, str(ROOT))


def main():
    from impact_qa.v26_data import FOLDER
    from impact_qa.v27_pipeline import prepare, run

    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'runner.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.prepare_only:
            prepare()
        else:
            asyncio.run(run(args.limit))


if __name__ == '__main__':
    main()
