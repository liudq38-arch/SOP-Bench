from hashlib import sha256

from impact_qa.common import ROOT, read_json


def verify_native_action(action, documents):
    source = action['source']
    path = ROOT / source['path']
    if source['path'] not in documents:
        documents[source['path']] = (read_json(path), sha256(path.read_bytes()).hexdigest())
    document, digest = documents[source['path']]
    if digest != source['sha256']:
        raise ValueError('evidence_audit:source_digest:' + source['path'])
    row = document['segments'][int(source['pointer'].rsplit('/', 1)[1])]
    names = {item['id']: item['name'] for item in document['action_labels']}
    raw = (row['start_frame'], row['end_frame']+1, row['entity'], row['phase'], row['anomaly_type'], names[row['action_label']])
    normalized = tuple(action[key] for key in ['start_frame', 'end_frame_exclusive', 'hand', 'phase', 'labels', 'action'])
    if raw != normalized:
        raise ValueError('evidence_audit:source_content:' + str(source))
    return source['path'], source['pointer']
