import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_dir', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    trees = sorted((args.model_dir / '.cache/huggingface/trees').glob('*.json'), key=lambda p: p.stat().st_mtime)
    if not trees:
        raise SystemExit('model_integrity:no_huggingface_tree')
    tree = json.loads(trees[-1].read_text())['files']
    files = []
    complete = True
    for relative, metadata in sorted(tree.items()):
        path = args.model_dir / relative
        item = {'path': relative, 'expected_size': metadata.get('size'), 'actual_size': path.stat().st_size if path.exists() else None, 'status': 'ok'}
        if not path.is_file():
            item['status'] = 'missing'
        elif item['actual_size'] != item['expected_size']:
            item['status'] = 'size_mismatch'
        elif metadata.get('lfs_sha256'):
            item['sha256'] = sha256(path)
            if item['sha256'] != metadata['lfs_sha256']:
                item['status'] = 'sha256_mismatch'
        complete = complete and item['status'] == 'ok'
        files.append(item)
    incomplete = sorted(p.relative_to(args.model_dir).as_posix() for p in args.model_dir.rglob('*.incomplete'))
    blocking_incomplete = []
    for relative in incomplete:
        candidate = Path(relative)
        if candidate.parent != Path('.cache/huggingface/download'):
            name = candidate.name.rsplit('.incomplete', 1)[0]
            if name not in tree or not (args.model_dir / name).is_file():
                blocking_incomplete.append(relative)
            continue
        name = candidate.name.rsplit('.incomplete', 1)[0]
        if name in tree and not (args.model_dir / name).is_file():
            blocking_incomplete.append(relative)
    report = {'model_dir': str(args.model_dir), 'tree_file': str(trees[-1]), 'expected_files': len(tree), 'checked_files': len(files), 'incomplete_files': incomplete, 'blocking_incomplete_files': blocking_incomplete, 'complete': complete and not blocking_incomplete, 'files': files}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: report[k] for k in ['model_dir', 'tree_file', 'expected_files', 'checked_files', 'incomplete_files', 'blocking_incomplete_files', 'complete']}, ensure_ascii=False, indent=2))
    if not report['complete']:
        for item in files:
            if item['status'] != 'ok':
                print(json.dumps(item, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
