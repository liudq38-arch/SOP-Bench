from jsonschema import Draft202012Validator


def validate_result(value, schema, record):
    Draft202012Validator(schema).validate(value)
    target=record['case']['target'];frames={f['frame_index']:f for f in record['frames']}
    allowed={s['id'] for s in record['sop']['steps']}|{'unknown'}
    if value['matched_sop_step'] not in allowed:raise ValueError('matched_sop_step must quote a provided ID')
    verdict=value['verdict'];kind=value['anomaly_type'];sub=value['redundant_subtype'];redundant=value['is_redundant_action']
    if verdict!='anomaly' and (kind!='none' or redundant or sub!='none'):raise ValueError('non-anomaly verdict requires none/false/none')
    if verdict=='anomaly' and kind=='none':raise ValueError('anomaly requires a specific type')
    if verdict=='insufficient_evidence' and value['confidence']>.4:raise ValueError('insufficient_evidence confidence must be <=0.4')
    if kind=='redundant' and not redundant:raise ValueError('redundant type requires is_redundant_action=true')
    if redundant != (sub!='none'):raise ValueError('redundant flag and subtype must agree')
    if verdict in ['anomaly','normal'] and not value['evidence_frames']:raise ValueError('anomaly/normal needs target evidence frames')
    if verdict=='anomaly' and not value['evidence_actions']:raise ValueError('anomaly needs evidence_actions')
    if len(value['reason'])>80:raise ValueError('reason must be <=80 Chinese characters')
    if not value['reason'].strip() or not value['expected_vs_observed'].strip():raise ValueError('reason and comparison must be nonempty')
    for index in value['evidence_frames']:
        if index not in frames or frames[index]['role']!='target':raise ValueError('evidence_frames must be target frame indices')
        if not target['start_s']-1e-6<=frames[index]['clip_timestamp_s']<target['end_s']:raise ValueError('evidence frame timestamp outside target')
    for action in value['evidence_actions']:
        a,b=action['t_start'],action['t_end']
        if not target['start_s']<=a<b<=target['end_s']:raise ValueError('evidence_action timestamp outside target or nonpositive')
        if not any(a-1e-6<=frames[i]['clip_timestamp_s']<=b+1e-6 for i in value['evidence_frames']):raise ValueError('evidence_action must contain a cited target frame time')
    if verdict=='anomaly' and not any(a['hand']==target['hand'] for a in value['evidence_actions']):raise ValueError('anomaly must include specified-hand evidence')
    if sub=='repeated_attempt' and len(value['evidence_frames'])<2:raise ValueError('repeated_attempt needs >=2 target frames')
    return value
