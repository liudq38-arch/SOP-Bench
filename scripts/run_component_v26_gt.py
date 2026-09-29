import os
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPACT_V26_CONFIG'] = 'configs/impact_qa/component_v26_gt.json'
runpy.run_path(str(ROOT / 'scripts/run_component_v26.py'), run_name='__main__')
