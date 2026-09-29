import copy

from .quality_v16 import require, validate as validate_frozen
from scripts.qualify_evidence_v17 import validate as qualify_frozen


def private_text_view(value, stage):
    view = copy.deepcopy(value)
    warnings = []

    def check(container, key, word_limit, path):
        if key not in container:
            return
        text = container[key]
        require(isinstance(text, str), 'private_text_type:' + path)
        require(len(text) <= 2000, 'private_text_char_limit:' + path)
        words = text.split()
        if len(words) > word_limit:
            warnings.append({'field': path, 'kind': 'private_text_word_budget', 'words': len(words), 'recommended_max': word_limit, 'original_preserved': True})
            container[key] = ' '.join(words[:word_limit])

    if stage == 'generate':
        check(view, 'limitation', 45, 'limitation')
        for i, row in enumerate(view.get('claims', [])):
            check(row, 'claim', 35, f'claims/{i}/claim')
    elif stage == 'blind':
        for key in ['observation', 'limitation']:
            check(view, key, 45, key)
    elif stage == 'visual_audit':
        check(view, 'counterevidence', 45, 'counterevidence')
        for i, row in enumerate(view.get('claim_checks', [])):
            check(row, 'observation', 25, f'claim_checks/{i}/observation')
        for i, row in enumerate(view.get('option_checks', [])):
            check(row, 'reason', 25, f'option_checks/{i}/reason')
    elif stage == 'source_audit':
        check(view, 'reason', 60, 'reason')
        for i, text in enumerate(view.get('unsupported_claims', [])):
            wrapped = {'text': text}
            check(wrapped, 'text', 60, f'unsupported_claims/{i}')
            view['unsupported_claims'][i] = wrapped['text']
    elif stage == 'qualify':
        check(view, 'limitation', 60, 'limitation')
        for i, row in enumerate(view.get('observations', [])):
            check(row, 'fact', 40, f'observations/{i}/fact')
    return view, warnings


def validate_stage(stage, value, case, generation=None):
    require(isinstance(value, dict), 'response_not_object')
    view, warnings = private_text_view(value, stage)
    validate_frozen(stage, view, case, generation)
    return copy.deepcopy(value), warnings


def validate_qualification(value, payload):
    require(isinstance(value, dict), 'qualification_not_object')
    view, warnings = private_text_view(value, 'qualify')
    qualify_frozen(view, payload)
    return copy.deepcopy(value), warnings
