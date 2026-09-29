import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import torch
from vllm.multimodal.media.image import ImageMediaIO
from vllm.multimodal.media.video import VideoMediaIO

from impact_qa.common import ROOT, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.descriptive_v21 import digest
from impact_qa.event_v22 import CONFIG, FOLDER, base_payload, gt_rows, key_images


def main():
    if not torch.cuda.is_available() or torch.cuda.device_count() < 6:
        raise RuntimeError('prepare_v22:cuda_unavailable_or_insufficient')
    services = []
    for url in CONFIG['base_urls']:
        r = httpx.get(url + '/models', trust_env=False, timeout=10)
        r.raise_for_status()
        if CONFIG['model'] not in [m['id'] for m in r.json()['data']]:
            raise RuntimeError(f'prepare_v22:model_not_served:{url}')
        services.append({'url': url, 'status': r.status_code})
    records = read_jsonl(ROOT / CONFIG['source_cases'])
    paths = set()
    first = []
    for record in records:
        case = record['case']
        for source in case['source_catalog']:
            p = ROOT / source['path']
            if p not in paths:
                if digest(p) != source['sha256']:
                    raise ValueError(f'prepare_v22:gt_hash:{p}')
                paths.add(p)
        for clip in record['clips']:
            video = clip['video']
            if digest(video['path']) != video['sha256']:
                raise ValueError(f'prepare_v22:video_hash:{clip["clip_id"]}')
            decoded, meta = VideoMediaIO(ImageMediaIO(), **video['media_io_kwargs']['video']).load_file(Path(video['path']))
            ids = [clip['media_frames'][i]['frame_id'] for i in meta['frames_indices']]
            if ids != [f['frame_id'] for f in video['sampled_frames']]:
                raise ValueError(f'prepare_v22:server_sample_mapping:{clip["clip_id"]}')
            for f in clip['media_frames']:
                p = Path(f['path'])
                if p not in paths:
                    if digest(p) != f['sha256']:
                        raise ValueError(f'prepare_v22:image_hash:{p}')
                    paths.add(p)
        index = 3 if '403f880f' in case['case_id'] else 0
        clip = record['clips'][index]
        first.append({'case_id': case['case_id'], 'clip_id': clip['clip_id'], 'input': base_payload(case, clip, key_images(clip['core_frames'])), 'gt_rows': gt_rows(case, clip)})
    save_jsonl(FOLDER / 'first10_inputs.jsonl', first[:10])
    result = {'torch': torch.__version__, 'cuda': torch.version.cuda, 'cuda_available': True, 'device_count': torch.cuda.device_count(), 'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.total,memory.used', '--format=csv,noheader'], text=True), 'services': services, 'cases': len(records), 'media_clips_validated': sum(len(r['clips']) for r in records), 'hashes_checked': len(paths), 'server_sampling_reproduced': True, 'model': CONFIG['model'], 'native_frames_reused': sum(len(r['frames']) for r in records), 'cuda_le_12_1_verified': False}
    save_json(FOLDER / 'precheck.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    for row in first[:10]:
        print(json.dumps({'case_id': row['case_id'], 'core': row['input']['target_interval_s'], 'sampled_frames': len(row['input']['video_sample_frames']), 'images': len(row['input']['labeled_images']), 'gt_rows': len(row['gt_rows'])}), flush=True)


if __name__ == '__main__':
    main()
