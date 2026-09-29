import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact_qa.common import ROOT, fingerprint, read_json, save_json, save_jsonl


FILES = {
    'CC4D': 'captaincook4d_qa_pairs_updated.json',
    'Assembly101': 'assembly101_qa_pairs_updated.json',
    'EgoOops': 'egooops_qa_pair.json',
    'EPIC-Tent': 'epic_tent_qa_pair.json',
}
RULES = {
    'correctness_words': r'\b(correct(?:ly)?|incorrect(?:ly)?|proper(?:ly)?|wrong|right (?:way|order|tool|part)|as instructed|according to (?:the )?(?:instructions|recipe))\b',
    'attachment_installation': r'\b(attach(?:ed|ing|ment)?|install(?:ed|ing|ation)?|insert(?:ed|ing|ion)?|connect(?:ed|ing|ion)?|fasten(?:ed|ing)?|assembl(?:e|ed|ing|y)|reassembl(?:e|ed|ing)|fit(?:ted|ting)?|mount(?:ed|ing)?)\b',
    'explicit_step_completion': r'\bcomplet(?:e|ed|ing)\b.{0,35}\b(step|process|instruction|task|assembly)\b|\b(?:step|process|instruction|task)\b.{0,35}\b(?:completely|completed|in full|fully)\b|\b(?:performing this step completely|have i finished|did i finish the (?:step|task|process))\b',
    'result_or_extent': r'\b(successful(?:ly)?|secure(?:ly)?|stable|firm(?:ly)?|tight(?:ly)?|aligned|flush|fully|completely|in full|in place|dissolved|melted|cooked|straight|flat|thorough(?:ly)?)\b',
    'omission': r'\b(miss(?:ed|ing)?|skip(?:ped|ping)?|omit(?:ted|ting)?|omission|leave out|left out)\b',
    'unnecessary_action': r'\b(unnecessary|unneeded|redundant|needless)\b|\b(?:step|action)\b.{0,25}\bnecessary\b|\bnecessary\b.{0,25}\b(?:step|action)\b',
    'before_after_context': r'\b(before|after|previous(?:ly)?|prior to|next step|followed by|subsequent(?:ly)?)\b',
    'explicit_order_sequence': r'\b(order|sequence|sequencing|out.of.order)\b',
    'normative_order_explicit': r'\b(?:(?:correct|incorrect|wrong|proper|right) (?:order|sequence)|(?:order|sequence) (?:correct|incorrect|wrong)|out.of.order|too (?:early|late))\b',
    'error_diagnosis': r'\b(what went wrong|what (?:did i do wrong|did i do incorrectly|mistake|error)|why (?:did|do|was|were|is|am)|what should|how should|how can i (?:fix|correct))\b',
    'tools_explicit': r'\b(tool|tools|utensil|utensils|screwdriver|wrench|hammer|scissors|knife|spoon|fork|tongs|spatula|drill|pliers|peeler|whisk)\b',
    'quantity_measurement': r'\b(how (?:much|many)|amount|quantity|number of|exactly|precisely|\d+(?:\.\d+)?\s*(?:ml|milliliters?|grams?|g|cups?|tablespoons?|teaspoons?|tsp|tbsp|cloves?|pieces?|inches?|cm))\b',
    'duration_temperature': r'\b(how long|duration|seconds?|minutes?|hours?|temperature|degrees?|heat|heated|heating|boil(?:ing)?|cool(?:ing)?|wait(?:ing)?)\b',
    'location_orientation': r'\b(where|location|position|orientation|align(?:ed|ing|ment)?|slot|slots|hole|holes|on top of|underneath|upside.down|left (?:side|column)|right (?:side|column)|top row|bottom row|designated|vertically|horizontally|clockwise|counterclockwise)\b',
}


def form(question):
    text = question.strip().lower()
    if re.match(r'^(did|do|does|is|are|was|were|am|have|has|had|can|could|should|would|will)\b', text):
        return 'polar'
    if re.match(r'^(what|which|who|where|when|why|how)\b', text):
        return text.split()[0]
    return 'other'


def source_phase(record):
    if 'error_label' in record:
        return {'correct': 'correct', 'mistake': 'error', 'correction': 'recovery'}.get(record['error_label'], str(record['error_label']))
    return 'error' if record.get('is_error') else 'correct'


def summarize(rows):
    questions = Counter(r['normalized_question'] for r in rows)
    return {
        'qa_pairs': len(rows),
        'clips': len({(r['source'], r['record_index']) for r in rows}),
        'unique_questions': len(questions),
        'forms': dict(Counter(r['question_form'] for r in rows)),
        'source_phases': dict(Counter(r['source_phase'] for r in rows)),
        'answer_prefix': dict(Counter(r['answer_prefix'] for r in rows)),
        'features': {k: {'count': sum(k in r['features'] for r in rows), 'percent': round(100 * sum(k in r['features'] for r in rows) / len(rows), 2), 'unique_questions': len({r['normalized_question'] for r in rows if k in r['features']})} for k in RULES},
        'top_question_templates': questions.most_common(20),
        'qa_per_clip': dict(Counter(Counter((r['source'], r['record_index']) for r in rows).values())),
    }


def main():
    out = ROOT / 'reports/impact_qa/question_taxonomy'
    rows = []
    source_hashes = {}
    for source, filename in FILES.items():
        path = ROOT / 'annotations/egoerrorvqa' / filename
        records = read_json(path)
        source_hashes[filename] = fingerprint(records)
        for ri, record in enumerate(records):
            for qi, pair in enumerate(record['qa_pairs']):
                question, answer = pair['question'], pair['answer']
                features = [key for key, regex in RULES.items() if re.search(regex, question, re.I)]
                prefix = re.match(r'^\s*(yes|no)\b', answer, re.I)
                rows.append({'qa_id': f'{source}:{ri}:{qi}', 'source': source, 'record_index': ri, 'qa_index': qi, 'video_id': record['video_id'], 'start_s': record.get('start_time'), 'end_s': record.get('end_time'), 'question': question, 'answer': answer, 'normalized_question': ' '.join(question.lower().split()), 'question_form': form(question), 'question_prefix2': ' '.join(question.lower().split()[:2]), 'source_phase': source_phase(record), 'answer_prefix': prefix.group(1).lower() if prefix else 'other', 'features': features, 'answer_order_words': bool(re.search(r'\b(order|sequence|before|after|earlier|later)\b', answer, re.I)), 'evidence_ref': f'annotations/egoerrorvqa/{filename}#/{ri}/qa_pairs/{qi}', 'source_error': {k: record[k] for k in ['error_label', 'error_annotation', 'errors', 'error_caption'] if k in record}})
    assert len(rows) == 3560 and len({r['qa_id'] for r in rows}) == 3560
    report = {'method': 'Deterministic question-text feature coding, multi-label and not an official/manual semantic taxonomy. Counts refer to question wording, not error-type frequencies or correctness. Answer content and source labels are not used for question-feature assignment.', 'rules': RULES, 'source_content_hashes': source_hashes, 'overall': summarize(rows), 'by_source': {s: summarize([r for r in rows if r['source'] == s]) for s in FILES}, 'phase_answer_crosstab': {p: dict(Counter(r['answer_prefix'] for r in rows if r['source_phase'] == p)) for p in ['correct', 'error', 'recovery']}}
    examples = {}
    assembly = [r for r in rows if r['source'] == 'Assembly101']
    report['assembly_deep_dive'] = {
        'feature_phase_crosstabs': {key: dict(Counter(r['source_phase'] for r in assembly if key in r['features'])) for key in RULES},
        'feature_answer_crosstabs': {key: dict(Counter(r['answer_prefix'] for r in assembly if key in r['features'])) for key in RULES},
        'answer_order_words': sum(r['answer_order_words'] for r in assembly),
        'source_order_related_qa': sum('order' in str(r['source_error'].get('error_annotation', '')).lower() or 'previous' in str(r['source_error'].get('error_annotation', '')).lower() for r in assembly),
        'source_order_related_clips': len({r['record_index'] for r in assembly if 'order' in str(r['source_error'].get('error_annotation', '')).lower() or 'previous' in str(r['source_error'].get('error_annotation', '')).lower()}),
    }
    for key in RULES:
        selected = []
        for source in FILES:
            pool = [r for r in rows if key in r['features'] and r['source'] == source]
            frequency = Counter(r['normalized_question'] for r in pool)
            seen = set()
            for row in sorted(pool, key=lambda r: (-frequency[r['normalized_question']], r['qa_id'])):
                if row['normalized_question'] in seen:
                    continue
                seen.add(row['normalized_question'])
                selected.append(dict(row, repeated_question_count=frequency[row['normalized_question']]))
                if len(seen) == 5:
                    break
        examples[key] = selected
    save_json(out / 'summary.json', report)
    save_jsonl(out / 'all_qa_coded.jsonl', rows)
    save_json(out / 'examples.json', examples)
    save_json(out / 'first10.json', rows[:10])
    procedure_path = ROOT / 'annotations/egoerrorvqa/procedure.json'
    procedure = read_json(procedure_path)['toy car assembly']
    assembly_records = read_json(ROOT / 'annotations/egoerrorvqa' / FILES['Assembly101'])
    packets = []
    for ri, record in enumerate(assembly_records[:10]):
        writer = {'procedure_text': procedure, 'current_action': {key: record[key] for key in ['verb', 'first_object', 'second_object']}, 'reference_annotation': {key: record[key] for key in ['error_label', 'error_annotation']}, 'task_id': record['task_id'], 'video_id': record['video_id'], 'start_s': record['start_time'], 'end_s': record['end_time']}
        evaluation = {'procedure_text': procedure, 'question': record['qa_pairs'][0]['question'], 'task_id': record['task_id'], 'video_id': record['video_id'], 'start_s': record['start_time'], 'end_s': record['end_time']}
        assert not {'error_label', 'error_annotation', 'answer', 'reference_annotation'} & evaluation.keys()
        packets.append({'source_record_index': ri, 'writer_input_reconstruction': writer, 'evaluation_input_reconstruction': evaluation, 'note': 'Writer packet reconstructs disclosed fields, not an unpublished original request. Evaluation packet preserves published input information, not its A2A wire encoding. No graph is supplied by this source.'})
    save_json(out / 'assembly101_input_first10.json', packets)
    lines = ['# 全库问句形式与特征统计', '', report['method'], '', '| 来源 | 片段 | QA | 唯一问句 |', '|---|---:|---:|---:|']
    for s, stats in report['by_source'].items():
        lines.append(f"| {s} | {stats['clips']} | {stats['qa_pairs']} | {stats['unique_questions']} |")
    lines += ['', '| 非互斥文本特征 | 全库 | CC4D | Assembly101 | EgoOops | EPIC-Tent |', '|---|---:|---:|---:|---:|---:|']
    for key in RULES:
        vals = [report['overall']['features'][key]] + [report['by_source'][s]['features'][key] for s in FILES]
        lines.append('| ' + key + ' | ' + ' | '.join(f"{v['count']} ({v['percent']}%)" for v in vals) + ' |')
    lines += ['', '## 句式', '', '```json', json.dumps(report['overall']['forms'], ensure_ascii=False, indent=2), '```', '', '## 示例索引', '', 'examples.json 保留每项每来源最多 5 个不同问句及原答案、原始标签、精确 JSON 索引；all_qa_coded.jsonl 保留全量逐题编码，可复核规则边界。']
    (out / 'counts.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: report['overall'][k] for k in ['qa_pairs', 'clips', 'unique_questions', 'forms', 'features', 'qa_per_clip']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
