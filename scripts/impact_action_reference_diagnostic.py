import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.api import Pool
from impact_qa.common import ANNOTATIONS, OUT, REPORTS, ROOT, fingerprint, read_json, read_jsonl, save_json, save_jsonl
from impact_qa.gt_qa import reference, verify_reference


FOLDER = OUT / 'gt_v13_action_reference'


def prepare():
    FOLDER.mkdir(exist_ok=True)
    video = 'AL07EJ17_Reassembly_A_003_front'
    path = ANNOTATIONS / 'TAS-S/front' / (video + '.json')
    annotation = read_json(path)
    names = sorted(['install_rotor_assembly', 'attach_adapter_plate', 'insert_bearing_plate_assembly', 'install_locking_lever_assembly', 'screw_on_anti_vibration_handle'])
    examples = []
    for name in names:
        i, segment = next((i, s) for i, s in enumerate(annotation['segments']) if s['label'] == name)
        start, end = segment['f_start'], segment['f_end'] - 1
        nums = [min(start + 8, end), (start + end) // 2, max(start, end - 8)]
        ref = reference(path, f'/segments/{i}')
        verify_reference(ref)
        examples.append({'action_name': name, 'frames': nums, 'source': ref})
    wanted = {n for c in examples for n in c['frames']}
    frames = {}
    source = Path('/data_1/ldq/dataset/impact/IMPACT-v1.1/videos/front') / (video + '.mp4')
    with av.open(str(source)) as container:
        container.streams.video[0].thread_type = 'AUTO'
        for n, frame in enumerate(container.decode(video=0)):
            if n in wanted:
                assert abs(float(frame.pts * frame.time_base) - n / 30) < 1e-5
                frames[n] = frame.to_image()
            if n >= max(wanted):
                break
    assert len(frames) == len(wanted)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    refs = []
    for i, c in enumerate(examples):
        board = Image.new('RGB', (1152, 350), 'white')
        draw = ImageDraw.Draw(board)
        draw.text((8, 3), 'TRAINING ACTION EXAMPLE: ' + c['action_name'].replace('_', ' '), fill='black', font=font)
        draw.text((8, 32), 'Different execution. GT action label, not a pixel-level part label or required order.', fill='black')
        for j, n in enumerate(c['frames']):
            im = ImageOps.pad(frames[n].crop((400, 250, 920, 650)), (384, 288), color='white')
            board.paste(im, (384 * j, 60))
        image_path = FOLDER / (fingerprint(c['action_name'])[:20] + '.jpg')
        board.save(image_path, quality=95)
        c.update(image_path=str(image_path), crop_xyxy=[400, 250, 920, 650], sha256=hashlib.sha256(image_path.read_bytes()).hexdigest())
        refs.append({'evidence_id': f'action_demo_{i}', 'path': str(image_path), 'requested_time_s': 0, 'time_scope': 'TRAINING REFERENCE ONLY, different execution. Placeholder time zero is not target time. Example GT action: ' + c['action_name'].replace('_', ' '), 'view': 'training_action_reference', 'sha256': c['sha256']})
    save_json(FOLDER / 'provenance.json', {'source_video': video, 'examples': examples, 'example_order': 'alphabetical_not_temporal', 'source_execution_disjoint_from_v13_targets': True, 'human_pixel_labels': False})
    save_jsonl(FOLDER / 'references.jsonl', refs)


def prepare_glossary():
    provenance = read_json(FOLDER / 'provenance.json')
    video = provenance['source_video']
    coarse_path = ANNOTATIONS / 'TAS-S/front' / (video + '.json')
    fine_path = ANNOTATIONS / 'TAS-B/front' / (video + '.json')
    coarse, fine = read_json(coarse_path), read_json(fine_path)
    names = {r['id']: r['name'] for r in fine['action_labels']}
    stages = sorted(e['action_name'] for e in provenance['examples'])
    support = {}
    for stage in stages:
        matches = []
        for i, atom in enumerate(fine['segments']):
            name = names[atom['action_label']]
            if atom['phase'] != 'normal' or atom['action_label'] == 0 or name.startswith(('hold_', 'pick_up_', 'store_', 'transfer_', 'align_')):
                continue
            center = (atom['start_frame'] + atom['end_frame']) / 2
            match = next(((j, s) for j, s in enumerate(coarse['segments']) if s['label'] == stage and s['f_start'] <= center < s['f_end']), None)
            if match:
                matches.append({'action': name, 'fine_reference': reference(fine_path, f'/segments/{i}'), 'coarse_reference': reference(coarse_path, f'/segments/{match[0]}')})
        support[stage] = matches
    public = []
    for stage, matches in support.items():
        unique = sorted({m['action'] for m in matches if not any(m['action'] in {other['action'] for other in rows} for key, rows in support.items() if key != stage)})
        public.append({'coarse_step_name': stage.replace('_', ' '), 'associated_fine_actions_unordered': [name.replace('_', ' ') for name in unique]})
    save_json(FOLDER / 'glossary_provenance.json', {'source_video': video, 'support': support, 'public_glossary': public, 'rule': 'Normal atomic-segment midpoint inside coarse step; remove generic hold/pick/store/transfer/align and actions appearing in multiple coarse steps. One training execution; associative, not exhaustive or normative.'})
    return public


async def run(with_glossary=False, kind='observed_order'):
    cases = [c for c in read_jsonl(OUT / 'gt_v13_inputs/cases.jsonl') if c['kind'] == kind and c['condition'] == 'dense_crop']
    references = read_jsonl(FOLDER / 'references.jsonl')
    prompt = (ROOT / 'prompts/impact_qa/v13/visual_review.txt').read_text()
    prompt += '\nFive additional TRAINING ACTION EXAMPLE cards are supplied after the twenty target images. Their captions are GT action labels of a DIFFERENT training execution. They can help recognize actions but do not specify current execution order or correctness. Their order is alphabetical, not temporal. A card labels an action interval, not individual object pixels. The placeholder timestamp zero is not an event time. Compare appearance without copying the example procedure as the answer.\n'
    glossary = prepare_glossary() if with_glossary else None
    if glossary is not None:
        prompt += '\nAn unordered coarse-step to fine-action glossary is supplied from the SAME OTHER training execution as the reference cards. It explains label granularity: a coarse installation step may start with manipulating one of its subcomponents. It does not identify any action in the current target frames, is not exhaustive, and gives no required order. Use only visually supported correspondence.\n'
    variant = 'action_glossary' if with_glossary else 'action_reference'
    if kind != 'observed_order':
        variant = kind + '_' + variant
    pool = Pool([f'http://127.0.0.1:{p}/v1' for p in [8000, 8001, 8002]], 4)
    async def process(c):
        payload = {'question': c['question'], 'public_procedure': c['public_procedure'], 'original_start_s': c['start_frame'] / 30, 'original_end_s_exclusive': (c['end_frame_inclusive'] + 1) / 30, 'event_images': [{'id': im['evidence_id'], 'time_s': im['requested_time_s']} for im in c['image_refs']], 'training_reference_names': [r['time_scope'] for r in references]}
        if glossary is not None:
            payload['training_label_glossary'] = glossary
        result = await pool.call('gt_v13_' + variant + '_visual', prompt, payload, c['image_refs'] + references, max_tokens=850)
        record = {'contract_id': c['contract_id'], 'condition': 'dense_crop_' + variant, 'visual_review': result['result'], 'cache_key': result['cache_key']}
        save_json(OUT / ('gt_v13/' + variant + '_runs') / (c['contract_id'] + '.json'), record)
        print(json.dumps(record), flush=True)
        return record
    try:
        records = await asyncio.gather(*(process(c) for c in cases))
    finally:
        await pool.close()
    save_jsonl(OUT / ('gt_v13/' + variant + '_results.jsonl'), records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--with-glossary', action='store_true')
    parser.add_argument('--kind', choices=['observed_order', 'component_installed'], default='observed_order')
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        asyncio.run(run(args.with_glossary, args.kind))
