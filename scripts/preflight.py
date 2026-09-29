import importlib.util
import json
import platform
import shutil
import subprocess
from pathlib import Path


def main():
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "disk_free_bytes": shutil.disk_usage(".").free,
        "pdftotext": shutil.which("pdftotext"),
        "scope": "CPU-only literature and annotation validation",
    }
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv"],
        capture_output=True,
        text=True,
        check=False,
    )
    result["nvidia_smi"] = gpu.stdout.strip() or gpu.stderr.strip()
    if importlib.util.find_spec("torch"):
        import torch

        result["torch"] = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count(),
            "build_cuda": torch.version.cuda,
        }
    else:
        result["torch"] = "not installed in this interpreter; not required for this task"
    Path("reports/preflight.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
