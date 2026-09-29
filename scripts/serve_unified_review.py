import os
import sys
from pathlib import Path

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from impact_qa.common import OUT
from scripts import serve_component_v26_gt_review


def build_app():
    return gr.TabbedInterface(
        [serve_component_v26_gt_review.build_app()],
        tab_names=['最新：GT-only QA'],
        title='IMPACT QA 人工审核',
        analytics_enabled=False,
    )


def main():
    allowed = [OUT / 'component_v26_gt_r1/media', OUT / 'component_v26_gt_r1/review_media', OUT / 'component_v26_r1/media']
    build_app().queue(default_concurrency_limit=2).launch(server_name='0.0.0.0', server_port=7863, share=False, allowed_paths=[str(p) for p in allowed], show_error=True)


if __name__ == '__main__':
    main()
