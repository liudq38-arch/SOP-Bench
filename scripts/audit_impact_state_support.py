import json
import sys
from collections import Counter
from graphlib import TopologicalSorter, CycleError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ANNOTATIONS, REPORTS, ROOT, read_json, save_json, save_jsonl


def main():
    rows, videos = [], []
    for path in sorted((ANNOTATIONS / 'ASR/annotations').glob('*.json')):
        data = read_json(path)
        sequence = data['state_sequence']
        assert sequence and sequence[0]['frame'] == 0
        previous = sequence[0]['state']
        frames = [x['frame'] for x in sequence]
        assert frames == sorted(set(frames))
        videos.append({'video_id': data['video_id'], 'workflow': data['workflow'], 'states': len(sequence), 'fps': data['fps']})
        for si, current in enumerate(sequence[1:], 1):
            state = current['state']
            assert len(state) == len(previous) == len(data['components'])
            for index, (before, after) in enumerate(zip(previous, state)):
                if before != after:
                    rows.append({'video_id': data['video_id'], 'workflow': data['workflow'], 'view': 'front', 'frame': current['frame'], 'time_s': current['frame'] / data['fps'], 'component': data['components'][index]['name'], 'state_index': index, 'before': before, 'after': after, 'source_ref': str(path.relative_to(ROOT)) + f'#/state_sequence/{si}', 'time_basis': 'front annotation nominal fps; ego synchronization not verified'})
            previous = state
    graph = read_json(ROOT / 'sources/impact_code/tasks/PSR/gemini_3_1_pro/configs/procedure_graph.json')
    adjacency = {node: set() for node in graph['nodes']}
    for edge in graph['edges']:
        source, target = edge[:2] if isinstance(edge, list) else (edge['source'], edge['target'])
        adjacency.setdefault(target, set()).add(source)
    try:
        order = list(TopologicalSorter(adjacency).static_order())
        dag = {'is_dag': True, 'node_count': len(order)}
    except CycleError as exc:
        dag = {'is_dag': False, 'error': str(exc)}
    summary = {'asr_videos': len(videos), 'workflow_counts': dict(Counter(v['workflow'] for v in videos)), 'component_count': 17, 'state_rows_including_initial': sum(v['states'] for v in videos), 'component_transitions': len(rows), 'transitions': dict(Counter(f'{r["before"]}->{r["after"]}' for r in rows)), 'by_workflow': {w: dict(Counter(f'{r["before"]}->{r["after"]}' for r in rows if r['workflow'] == w)) for w in ['assemble', 'disassemble']}, 'graph': {'metadata': graph['meta'], 'edge_count': len(graph['edges']), **dag, 'authority': 'mined_candidate; not a human-verified normative SOP'}, 'limits': 'Transitions can update multiple component states at the same frame and are not independent physical installation counts. State vectors do not directly specify parent attachment relations. Front timestamps cannot be reused as ego timestamps without synchronization.'}
    folder = REPORTS / 'question_taxonomy'
    save_json(folder / 'impact_state_support.json', summary)
    save_jsonl(folder / 'impact_component_transitions.jsonl', rows)
    save_json(folder / 'impact_state_first10.json', rows[:10])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
