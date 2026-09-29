from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
import uvicorn


ROOT = Path(__file__).resolve().parents[1]
app = Starlette(routes=[Mount('/', app=StaticFiles(directory=ROOT / 'apps/impact_assembly_3d', html=True, follow_symlink=True))])


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7864, log_level='info')
