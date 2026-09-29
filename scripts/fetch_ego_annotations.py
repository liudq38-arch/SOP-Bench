import concurrent.futures
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.assets import read_json, sha256


def main():
    tree = read_json("sources/ego_tree.json")
    revision = tree["sha"]
    entries = [item for item in tree["tree"] if item["type"] == "blob" and item["path"].startswith("data/json/")]

    def download(item):
        url = f"https://api.github.com/repos/z1oong/EgoErrorVQA/git/blobs/{item['sha']}"
        path = Path("annotations/egoerrorvqa") / Path(item["path"]).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size != item["size"]:
            response = subprocess.run(
                ["curl", "-fLs", "--connect-timeout", "5", "--max-time", "30", url],
                capture_output=True, check=True,
            )
            content = base64.b64decode(json.loads(response.stdout)["content"])
            temporary = path.with_suffix(".json.part")
            temporary.write_bytes(content)
            if len(content) != item["size"]:
                raise RuntimeError(f"EgoErrorVQA download size mismatch: {path}")
            temporary.replace(path)
        content = path.read_bytes()
        blob_hash = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if blob_hash != item["sha"]:
            raise RuntimeError(f"EgoErrorVQA download blob mismatch: {path}")
        read_json(path)
        return {"path": str(path), "url": url, "revision": revision, "bytes": path.stat().st_size, "sha256": sha256(path)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(download, entries))
    Path("reports/ego_download_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
