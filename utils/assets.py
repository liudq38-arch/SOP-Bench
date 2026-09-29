import hashlib
import json
import urllib.request
from pathlib import Path


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fetch_small(url, destination, limit=30_000_000, expected_size=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and (expected_size is None or destination.stat().st_size == expected_size):
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchAnnotationAudit/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as handle:
            declared = int(response.headers.get("Content-Length", 0))
            if declared > limit:
                raise ValueError(f"asset exceeds limit: {declared} > {limit}")
            total = 0
            while chunk := response.read(262144):
                total += len(chunk)
                if total > limit:
                    raise ValueError(f"asset exceeds limit: {total} > {limit}")
                handle.write(chunk)
        if expected_size is not None and temporary.stat().st_size != expected_size:
            raise ValueError(f"size mismatch: {temporary.stat().st_size} != {expected_size}")
        temporary.replace(destination)
        return destination
    except Exception as error:
        raise RuntimeError(f"asset download failed: {url} -> {destination}: {error}") from error
