from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from impact_qa.browser_checks import firefox_check
from impact_qa.common import read_json, save_json


def main():
    out = ROOT / 'outputs/impact_qa/assembly_3d/complete_videos/browser'
    rows = read_json(ROOT / 'apps/impact_assembly_3d/assembly_videos.json')['videos']
    checks = []
    with firefox_check(out) as browser:
        browser.call('POST', '/window/rect', {'width': 1400, 'height': 1050})
        browser.open('http://127.0.0.1:7864/videos.html')
        browser.wait('return document.querySelectorAll("video").length===2 && [...document.querySelectorAll("video")].every(v=>v.readyState>=1);')
        browser.execute("window.checkErrors=[];window.addEventListener('error',e=>window.checkErrors.push(e.message));window.addEventListener('unhandledrejection',e=>window.checkErrors.push(String(e.reason)));")
        for row in rows:
            model = row['model']
            info = browser.execute("const c=document.getElementById(arguments[0]);c.scrollIntoView();const v=c.querySelector('video');return {duration:v.duration,width:v.videoWidth,height:v.videoHeight};", model)
            assert abs(info['duration']-row['duration_s']) < .04, info
            browser.execute("document.getElementById(arguments[0]).querySelector('video').play();", model)
            browser.wait(f"return document.querySelector('#{model} video').currentTime>.2;")
            browser.execute("document.getElementById(arguments[0]).querySelector('video').pause();", model)
            browser.execute("document.getElementById(arguments[0]).querySelector('.steps button:nth-child(3)').click();", model)
            browser.wait(f"const v=document.querySelector('#{model} video');return !v.seeking && Math.abs(v.currentTime-{row['steps'][2]['start_s']})<.1;")
            browser.execute("document.getElementById(arguments[0]).querySelector('.anomalies button').click();", model)
            browser.wait(f"return document.querySelector('#{model} .live').classList.contains('active');")
            browser.screenshot(out / f'{model}_anomaly.png')
            browser.execute("const v=document.getElementById(arguments[0]).querySelector('video');v.currentTime=arguments[1]-.15;", model, row['duration_s'])
            browser.wait(f"const v=document.querySelector('#{model} video');return !v.seeking&&v.readyState>=2;")
            assert browser.execute("return !document.getElementById(arguments[0]).querySelector('video').error;", model)
            checks.append(dict(model=model, info=info, playback=True, stage_seek=True, anomaly_highlight=True, seek_to_end=True))
        assert browser.execute('return window.checkErrors;') == []
        browser.call('POST', '/window/rect', {'width': 430, 'height': 950})
        assert browser.execute('return document.documentElement.scrollWidth<=innerWidth+1;')
        browser.screenshot(out / 'mobile.png')
        for model in ['A', 'B']:
            browser.open('http://127.0.0.1:7864/?model='+model)
            browser.wait('return Boolean(window.assemblyViewer);')
            state = browser.execute('return window.assemblyViewer.getState();')
            assert state['model'] == model and state['webgl']
        save_json(out / 'verification.json', dict(status='passed', videos=checks, mobile_no_overflow=True, A_B_3d_still_work=True, client_errors=[]))
        print('PASS A/B video playback, stage/anomaly/end seek, highlights, mobile layout and both 3D entry points', flush=True)


if __name__ == '__main__':
    main()
