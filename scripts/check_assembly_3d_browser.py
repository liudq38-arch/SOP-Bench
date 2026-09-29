import base64
import json
import os
from pathlib import Path
import subprocess
import time

import httpx


ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'outputs/impact_qa/assembly_3d/b_animation_v2'
    out.mkdir(parents=True, exist_ok=True)
    profile = Path('/home/ldq/snap/firefox/common/codex-timeline-profiles')
    profile.mkdir(parents=True, exist_ok=True)
    log = (out / 'browser.log').open('w')
    process = subprocess.Popen(['geckodriver', '--host', '127.0.0.1', '--port', '4445', '--profile-root', str(profile)], stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'LIBGL_ALWAYS_SOFTWARE': '1'})
    client = httpx.Client(base_url='http://127.0.0.1:4445', timeout=90, trust_env=False)
    session = None

    def call(method, path, payload=None):
        response = client.request(method, path, json=payload)
        response.raise_for_status()
        value = response.json()['value']
        if isinstance(value, dict) and value.get('error'):
            raise RuntimeError('assembly_3d_browser: ' + str(value))
        return value

    try:
        for _ in range(20):
            try:
                call('GET', '/status')
                break
            except httpx.HTTPError:
                time.sleep(.3)
        args = [] if os.environ.get('ASSEMBLY_BROWSER_HEADED') else ['-headless']
        data = call('POST', '/session', {'capabilities': {'alwaysMatch': {'browserName': 'firefox', 'moz:firefoxOptions': {'args': args, 'prefs': {'webgl.force-enabled': True, 'webgl.disabled': False}}}}})
        session = data['sessionId']
        prefix = '/session/' + session

        def execute(script, *args):
            return call('POST', prefix + '/execute/sync', {'script': script, 'args': list(args)})

        def screenshot(name):
            time.sleep(1.2)
            (out / name).write_bytes(base64.b64decode(call('GET', prefix + '/screenshot')))

        def click(selector):
            element = call('POST', prefix + '/element', {'using': 'css selector', 'value': selector})['element-6066-11e4-a52e-4f735466cecf']
            call('POST', prefix + '/element/' + element + '/click', {})

        def state():
            return execute('return window.assemblyViewer.getState();')

        call('POST', prefix + '/window/rect', {'width': 1500, 'height': 1050})
        call('POST', prefix + '/url', {'url': 'http://127.0.0.1:7864'})
        for _ in range(40):
            if execute('return Boolean(window.assemblyViewer);'):
                break
            time.sleep(.25)
        else:
            screenshot('failure.png')
            raise RuntimeError('assembly_3d_browser: ' + execute("return document.getElementById('loading').textContent;"))
        execute("window.testErrors=[];window.addEventListener('error',e=>window.testErrors.push(e.message));window.addEventListener('unhandledrejection',e=>window.testErrors.push(String(e.reason)));")
        initial = state()
        assert initial['model'] == 'A' and initial['webgl'] and len(initial['parts']) == 15, initial
        screenshot('initial.png')
        click('#play')
        time.sleep(1)
        click('#play')
        paused = state()
        time.sleep(.5)
        assert paused['progress'] > 0 and not paused['playing']
        assert state()['progress'] == paused['progress']
        execute('window.assemblyViewer.seek(5.67/14);')
        assert state()['step'] == 5 and state()['tool'] == 'phillips'
        screenshot('adapter_screw.png')
        click('#next')
        assert state()['step'] == 6
        click('#previous')
        assert state()['step'] == 5
        execute('window.assemblyViewer.seek(1);')
        screenshot('assembled.png')
        click('#disassemble')
        assert state()['mode'] == 'disassemble' and state()['step'] == 13
        execute('window.assemblyViewer.seek(10.65/14);')
        assert state()['step'] == 3 and state()['tool'] == 'wrench'
        assert '松开' in execute("return document.querySelector('#step-description').textContent;")
        screenshot('disassembly_nut.png')
        click('#xray')
        click('#top')
        click('#front')
        click('#home')
        execute("const s=document.querySelector('#explode');s.value=.8;s.dispatchEvent(new Event('input'));const m=document.querySelector('#model');m.value='B';m.dispatchEvent(new Event('change'));")
        assert state()['model'] == 'B' and state()['stepCount'] == 12
        assert not execute("return document.querySelector('#play').disabled;")
        assert not {'lever', 'leverScrew', 'adapterScrew0', 'adapterNut0'}.intersection(state()['parts'])
        assert {'housingScrew0', 'housingScrew1'}.issubset(state()['parts'])
        click('#assemble')
        b_start = state()['positions']
        screenshot('model_B_initial.png')
        click('#play')
        time.sleep(.6)
        click('#play')
        b_pause = state()['progress']
        time.sleep(.3)
        assert state()['progress'] == b_pause and b_pause > 0
        moving = ['rotor', 'pinion', 'shaftNut', 'housingScrew0', 'housingScrew1', 'adapter', 'bearing', 'bearingScrew0', 'bearingScrew1', 'handle']
        for i, part in enumerate(moving, 1):
            execute('window.assemblyViewer.seek(arguments[0]);', (i + .001) / 12)
            before = state()['positions'][part]
            execute('window.assemblyViewer.seek(arguments[0]);', (i + .999) / 12)
            after = state()['positions'][part]
            assert sum((a-b)**2 for a, b in zip(before, after)) > .01, (i, part)
        for index, expected in [(3, 'wrench'), (4, 'phillips'), (5, 'phillips'), (8, 'flat'), (9, 'flat')]:
            execute('window.assemblyViewer.seek(arguments[0]);', (index + .7) / 12)
            assert state()['tool'] == expected and state()['toolVisible'], state()
        click('#focus')
        screenshot('model_B_bearing_tool.png')
        execute('window.assemblyViewer.seek(4.7/12);')
        click('#focus')
        screenshot('model_B_housing_tool.png')
        click('#home')
        execute('window.assemblyViewer.seek(1);')
        b_complete = state()['positions']
        assert b_complete['adapter'][0] < b_complete['rotor'][0]
        screenshot('model_B_complete.png')
        click('#disassemble')
        assert state()['positions'] == b_complete
        execute('window.assemblyViewer.seek(2.7/12);')
        assert state()['step'] == 9 and state()['tool'] == 'flat'
        execute('window.assemblyViewer.seek(1);')
        assert state()['positions'] == b_start
        execute("document.querySelector('#b-reference').open=true;")
        assert execute("return document.querySelector('#b-reference img').naturalWidth>0;")
        execute("const m=document.querySelector('#model');m.value='A';m.dispatchEvent(new Event('change'));")
        click('#assemble')
        execute('window.assemblyViewer.seek(8.65/14);')
        assert state()['tool'] == 'torx' and state()['stepCount'] == 14
        assert state()['parts'] == initial['parts']
        assert execute("return document.querySelector('#b-reference').hidden;")
        call('POST', prefix + '/window/rect', {'width': 430, 'height': 930})
        time.sleep(.5)
        assert execute('return document.documentElement.scrollWidth<=innerWidth+1;')
        screenshot('mobile.png')
        errors = execute('return window.testErrors;')
        assert not errors, errors
        call('POST', prefix + '/url', {'url': 'http://127.0.0.1:7864/?model=B'})
        for _ in range(40):
            if execute('return Boolean(window.assemblyViewer);'):
                break
            time.sleep(.25)
        assert state()['model'] == 'B' and state()['stepCount'] == 12
        assert execute('return document.documentElement.scrollWidth<=innerWidth+1;')
        screenshot('model_B_mobile.png')
        result = {'status': 'passed', 'browser': data['capabilities']['browserVersion'], 'initial': initial, 'pause_stable_A_B': True, 'play_seek_previous_next': True, 'disassembly': True, 'tools': ['phillips', 'wrench', 'torx', 'flat'], 'B_steps': 12, 'B_moving_parts_checked': moving, 'B_reverse_endpoints_match': True, 'B_reference_image': True, 'B_direct_link': True, 'A_B_A_regression': True, 'mobile_no_horizontal_overflow': True, 'client_errors': errors}
        (out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        if session:
            try:
                call('DELETE', '/session/' + session)
            except Exception:
                pass
        client.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


if __name__ == '__main__':
    main()
