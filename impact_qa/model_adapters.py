from pathlib import Path

from .api import Client
from .common import fingerprint, read_json


def local_client(base_url, model_name, model_path, concurrency):
    model_path = Path(model_path)
    client = Client(base_url, concurrency)
    client.model = model_name
    client.model_revision = fingerprint({'config': read_json(model_path / 'config.json'), 'index': read_json(model_path / 'model.safetensors.index.json'), 'weight_files': [(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(model_path.glob('*.safetensors'))]})
    return client
