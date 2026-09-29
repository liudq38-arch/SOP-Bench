import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

from impact_qa.common import ROOT, fingerprint, read_json
from impact_qa.reliable_pool import ReliablePool
from impact_qa.release_gate import evaluate
from impact_qa.evidence_ids import normalize_evidence


class Backend:
    model = 'fake'
    model_revision = 'fake-v1'

    def __init__(self):
        self.calls = 0
        self.active = 0
        self.peak = 0
        self.fail = False

    async def call(self, stage, prompt, payload, images, max_tokens):
        self.calls += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        if self.fail:
            raise RuntimeError('injected_failure')
        return {'result': {'answer': payload['id']}}

    async def close(self):
        pass


class PoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_coalesce_distinct_and_failure_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            backend = Backend()
            pool = ReliablePool(backend, Path(temp))
            rows = await asyncio.gather(*(pool.call('s', 'p', {'id': 1}) for _ in range(12)))
            self.assertEqual(backend.calls, 1)
            rows[0]['result']['answer'] = 'mutated'
            self.assertEqual(rows[1]['result']['answer'], 1)
            await asyncio.gather(pool.call('s', 'p', {'id': 2}), pool.call('s', 'p', {'id': 3}))
            self.assertEqual(backend.peak, 2)
            backend.fail = True
            with self.assertRaises(RuntimeError):
                await pool.call('s', 'p', {'id': 4})
            backend.fail = False
            self.assertEqual((await pool.call('s', 'p', {'id': 4}))['result']['answer'], 4)
            self.assertEqual(len(list(Path(temp).glob('*.json'))), 5)
            await pool.close()


class GateTests(unittest.TestCase):
    def test_transport_ids_normalized_without_answer_change(self):
        raw = {'tool': 'wrench', 'evidence_image_ids': ['Frame target_2'], 'before_image_id': 'Frame target_1', 'after_image_id': 'Frame target_2'}
        refs = [{'evidence_id': 'target_1'}, {'evidence_id': 'target_2'}]
        normalized, changes = normalize_evidence(raw, refs)
        self.assertEqual(normalized['tool'], raw['tool'])
        self.assertEqual(set(normalized['evidence_image_ids']), {'target_1', 'target_2'})
        self.assertEqual(raw['before_image_id'], 'Frame target_1')
        self.assertTrue(changes)
        raw['before_image_id'] = 'target_99'
        with self.assertRaises(ValueError):
            normalize_evidence(raw, refs)

    def test_missing_severe_leakage_and_version_are_rejected(self):
        policy = read_json(ROOT / 'configs/impact_qa/release_v14.json')
        self.assertFalse(evaluate({}, policy)['release'])
        evidence = {'kind': 'tool_identity', 'policy_hash': fingerprint(policy), 'requirements': dict.fromkeys(policy['require'], True), 'metrics': copy.deepcopy(policy['thresholds']), 'review_source': 'research_agent_direct_evidence', 'pipeline_hash': 'frozen', 'reviewed_pipeline_hash': 'frozen'}
        self.assertTrue(evaluate(evidence, policy)['release'])
        for key, value in [('severe_defects', 1), ('min_independent_events_per_kind', 29), ('visual_evidence_pass_rate', 0.94), ('completion_rate', float('nan')), ('completion_rate', 2)]:
            bad = copy.deepcopy(evidence)
            bad['metrics'][key] = value
            self.assertFalse(evaluate(bad, policy)['release'])
        for key in ['no_gt_leakage', 'independent_trials']:
            bad = copy.deepcopy(evidence)
            bad['requirements'][key] = False
            self.assertFalse(evaluate(bad, policy)['release'])
        bad = copy.deepcopy(evidence)
        bad['review_source'] = 'model_self_review'
        self.assertFalse(evaluate(bad, policy)['release'])


if __name__ == '__main__':
    unittest.main()
