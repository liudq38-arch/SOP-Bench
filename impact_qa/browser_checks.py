import base64
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import time

import httpx


class BrowserCheck:
    def __init__(self, client):
        self.client = client
        self.prefix = ''

    def call(self, method, path, payload=None):
        response = self.client.request(method, self.prefix + path, json=payload)
        response.raise_for_status()
        data = response.json()['value']
        if isinstance(data, dict) and data.get('error'):
            raise RuntimeError('browser_check: ' + str(data))
        return data

    def execute(self, script, *args):
        return self.call('POST', '/execute/sync', {'script': script, 'args': list(args)})

    def wait(self, script, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.execute(script)
            if value:
                return value
            time.sleep(.2)
        raise TimeoutError('browser_check: ' + script)

    def open(self, url):
        self.call('POST', '/url', {'url': url})

    def screenshot(self, path):
        time.sleep(.6)
        Path(path).write_bytes(base64.b64decode(self.call('GET', '/screenshot')))


@contextmanager
def firefox_check(folder, port=4445):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    profile = Path('/home/ldq/snap/firefox/common/codex-timeline-profiles')
    profile.mkdir(parents=True, exist_ok=True)
    with (folder / 'browser.log').open('w') as log, httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=60, trust_env=False) as client:
        process = subprocess.Popen(['geckodriver', '--host', '127.0.0.1', '--port', str(port), '--profile-root', str(profile)], stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'LIBGL_ALWAYS_SOFTWARE': '1'})
        browser = BrowserCheck(client)
        try:
            for _ in range(30):
                try:
                    browser.call('GET', '/status')
                    break
                except httpx.HTTPError:
                    time.sleep(.2)
            args = [] if os.environ.get('DISPLAY') else ['-headless']
            data = browser.call('POST', '/session', {'capabilities': {'alwaysMatch': {'browserName': 'firefox', 'moz:firefoxOptions': {'args': args, 'prefs': {'webgl.force-enabled': True, 'media.autoplay.default': 0}}}}})
            browser.prefix = '/session/' + data['sessionId']
            yield browser
        finally:
            if browser.prefix:
                try:
                    browser.call('DELETE', '')
                except Exception:
                    pass
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
