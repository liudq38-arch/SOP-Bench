import copy

from impact_qa.atr_qa import KINDS, validate_generation


def validate_items(result,case,questions,positions):
    if set(result)!={'items'} or not isinstance(result['items'],list) or len(result['items'])!=len(KINDS) or {q.get('kind') for q in result['items']}!=set(KINDS):
        raise ValueError('atr_item:invalid_batch_schema')
    blank=[{'kind':k,'answerable':False,'question':questions[k],'answer':'','options':[],'correct_option':None,'source_ids':[],'image_ids':[],'evidence':'','grade':0,'limitation':'No validated draft.'} for k in KINDS]
    clean=[];errors=[]
    for q in result['items']:
        probe=copy.deepcopy(blank);probe[KINDS.index(q['kind'])]=q
        try:
            validate_generation({'items':probe},case)
            if q['question']!=questions[q['kind']]:raise ValueError('atr_item:question_protocol')
            if q['answerable'] and q['correct_option']!=positions[q['kind']]:raise ValueError('atr_item:option_position_protocol')
            clean.append(copy.deepcopy(q))
        except ValueError as exc:
            errors.append({'kind':q['kind'],'error':str(exc),'raw_item':copy.deepcopy(q)})
            item=copy.deepcopy(blank[KINDS.index(q['kind'])]);item['limitation']='Original generated draft failed evidence/schema validation: '+str(exc);clean.append(item)
    return {'items':clean,'item_validation_errors':errors}
