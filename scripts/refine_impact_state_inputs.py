import copy
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import OUT, REPORTS, fingerprint, read_jsonl, save_json, save_jsonl
from impact_qa.state_qa import STATE_OUT


def main():
    packets = read_jsonl(STATE_OUT / 'packets.jsonl')
    for packet in packets:
        packet.pop('input_hash', None)
        target = packet['target']
        comp = packet['computed_comparisons'][0]
        if comp['predecessor_component'] == 'screw_lever':
            comp['predecessor_component'] = 'lever'
            current = next(s for s in packet['component_states'] if s['id'] == comp['source_ids'][0])
            comp['predecessor_state_at_first_target_action'] = current['states']['lever']
        packet['answer_contract'] = {
            'target_at_end': {'component_id': target['component_id'], 'at_frame': target['end_frame_inclusive'], 'state': target['state_at_end'], 'source_id': target['end_state_source_id']},
            'predecessor_at_target_start': {'component_id': comp['predecessor_component'], 'at_frame': round(comp['time_s'] * packet['media_profile']['fps']), 'state': comp['predecessor_state_at_first_target_action'], 'source_id': comp['source_ids'][0]},
            'allowed_extra_claims': 'No additional component states or failure mechanisms in a completion answer. Use exact named components, not entire subassemblies.',
        }
        packet['require_state_assertions'] = True
        source = {'id': 'relation_handle_housing', 'kind': 'component_receiver_relation', 'path': 'sources/impact_docs/Manual_Book.svg', 'location': 'final operation in Reassembly row: side handle screws into gearbox housing', 'verification': 'research_agent_visual_transcription_pending_human', 'source_ids': ['official_manual'], 'scope': 'this illustrated Model-A development reference only'}
        mapping = {'component_id': 'anti_vibration_handle', 'receiver_id': 'gearbox_housing', 'relation': 'handle screwed into side of gearbox housing', 'verification_status': 'verified_by_research_agent_from_official_illustration; pending_human', 'source_ids': ['relation_handle_housing', 'official_manual']}
        packet['procedure']['state_mappings'] = [mapping]
        packet['procedure']['source_catalog'].append(source)
        packet['evidence_catalog'].append(source)
        packet['procedure']['unresolved'] = [x for x in packet['procedure']['unresolved'] if 'component-to-receiver' not in x]
        packet['procedure']['unresolved'].append('Only the handle-to-housing relation has a provisional research-agent visual mapping; other receivers remain unknown.')
        if target['component_id'] == 'anti_vibration_handle':
            target['receiver_id'] = 'gearbox_housing'
        frames = [r for r in packet['image_refs'] if r.get('media_type') != 'video']
        for ref in [frames[-4], frames[-1]]:
            path = Path(ref['path']).with_name(Path(ref['path']).stem + '_workcrop.jpg')
            Image.open(ref['path']).crop((500, 390, 820, 620)).resize((960, 690), Image.Resampling.LANCZOS).save(path, quality=94)
            cropped = copy.deepcopy(ref)
            cropped.update(evidence_id=ref['evidence_id'] + ':crop', path=str(path), view='front workspace crop, original pixels enlarged; crop xyxy=[500,390,820,620]', crop_xyxy=[500, 390, 820, 620])
            packet['image_refs'].append(cropped)
        packet['coverage']['sampling'] += '; two same-frame workspace crops added, no new temporal coverage'
        packet['input_hash'] = fingerprint(packet)
    folder = OUT / 'state_qa_inputs_v10_1'
    save_jsonl(folder / 'packets.jsonl', packets)
    save_json(folder / 'procedure.json', packets[0]['procedure'])
    save_json(REPORTS / 'v10_1_input_first10.json', packets[:10])
    print(json.dumps({'events': len(packets), 'input': str(folder / 'packets.jsonl'), 'state_assertions_required': True, 'extra_crops_per_event': 2, 'receiver_mapping': 'handle_to_housing_provisional_research_agent_mapping'}, indent=2))


if __name__ == '__main__':
    main()
