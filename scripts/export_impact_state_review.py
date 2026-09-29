import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, read_json, read_jsonl
from scripts.run_impact_state_qa import export


def main(args):
    packets = read_jsonl(args.input)
    records = [read_json(path) for path in sorted((OUT / args.version / 'runs').glob('*.json'))]
    ids = {r['event_id'] for r in records}
    export(records, [p for p in packets if p['event_id'] in ids], args.version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--input', type=Path, default=OUT / 'state_qa_inputs_v10_1/packets.jsonl')
    main(parser.parse_args())
