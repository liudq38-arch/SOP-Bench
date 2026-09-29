import asyncio
import copy
import uuid
from datetime import datetime, timezone

from .common import fingerprint, save_json


class ReliablePool:
    def __init__(self, backend, audit_dir):
        self.backend = backend
        self.audit_dir = audit_dir
        self.model = backend.model
        self.model_revision = backend.model_revision
        self.pending = {}
        self.started = 0
        self.coalesced = 0

    async def call(self, stage, prompt, payload, images=None, max_tokens=2048):
        key = fingerprint([self.model_revision, stage, prompt, payload, images or [], max_tokens])
        if key in self.pending:
            self.coalesced += 1
            return copy.deepcopy(await asyncio.shield(self.pending[key]))
        task = asyncio.create_task(self._execute(key, stage, prompt, payload, images or [], max_tokens))
        self.pending[key] = task
        task.add_done_callback(lambda done: self._finish(key, done))
        return copy.deepcopy(await asyncio.shield(task))

    def _finish(self, key, task):
        if self.pending.get(key) is task:
            del self.pending[key]
        if not task.cancelled():
            task.exception()

    async def _execute(self, key, stage, prompt, payload, images, max_tokens):
        self.started += 1
        audit = {'request_key': key, 'started_utc': datetime.now(timezone.utc).isoformat(), 'stage': stage, 'request': {'prompt': prompt, 'payload': payload, 'images': images, 'max_tokens': max_tokens}}
        path = self.audit_dir / (key + '_' + uuid.uuid4().hex + '.json')
        try:
            result = await self.backend.call(stage, prompt, payload, images, max_tokens=max_tokens)
            audit.update(status='ok', response=result)
            save_json(path, audit)
            return result
        except Exception as exc:
            audit.update(status='error', error=f'{type(exc).__name__}:{exc}')
            save_json(path, audit)
            raise

    async def close(self):
        await asyncio.gather(*list(self.pending.values()), return_exceptions=True)
        await self.backend.close()
