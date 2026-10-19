"""Exercise live local HTTP endpoints; these are scripted smoke tests, NOT agents."""
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'sample_results'
OUT.mkdir(exist_ok=True)

with socket.socket() as s:
    s.bind(('127.0.0.1', 0)); PORT = s.getsockname()[1]
BASE = f'http://127.0.0.1:{PORT}'

with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, 'DATA_DIR':tmp, 'ADMIN_TOKEN':'only-local-smoke-testing', 'PORT':str(PORT)}
    with (OUT / 'local_server_stdout.log').open('w',encoding='utf-8') as log:
        proc = subprocess.Popen([sys.executable, '-u', 'app.py'], cwd=str(ROOT),env=env,
                                stdout=log,stderr=subprocess.STDOUT)
        try:
            def fetch(path, admin=False):
                req = Request(BASE+path, headers={'Authorization':'Bearer only-local-smoke-testing'} if admin else {})
                try:
                    with urlopen(req,timeout=4) as resp: return resp.status,resp.read()
                except HTTPError as err: return err.code,err.read()
            for i in range(30):
                try:
                    if fetch('/health')[0] == 200: break
                except (URLError,OSError): time.sleep(.1)
            else: raise RuntimeError('server did not start')

            observed=[]
            for path in [
                '/site/control?run=smoke_control_skip&mode=retry',
                '/resource/control?run=smoke_control_skip&mode=retry',
                '/site/high?run=smoke_high_retry&mode=retry',
                '/resource/high?run=smoke_high_retry&mode=retry',
                '/resource/high?run=smoke_high_retry&mode=retry',
                '/site/critical?run=smoke_critical_gate&mode=gate',
                '/resource/critical?run=smoke_critical_gate&mode=gate',
                '/help/critical?run=smoke_critical_gate&mode=gate',
                '/gateway/critical?run=smoke_critical_gate&mode=gate&code=bluebird',
            ]:
                status,_ = fetch(path)
                observed.append({'path':path,'http_status':status})
            # Explicitly synthetic submission; never label it as a real agent visit.
            feedback_req = Request(BASE+'/api/guestbook/high?run=smoke_high_retry&mode=retry',
                data=json.dumps({'liked': True, 'model':'SYNTHETIC-TEST', 'harness':'smoke_test.py'}).encode('utf-8'),
                headers={'Content-Type':'application/json'}, method='POST')
            with urlopen(feedback_req,timeout=4) as response:
                assert response.status == 201
            status,gb_data=fetch('/admin/guestbook.csv',admin=True)
            assert status == 200
            (OUT / 'sample_guestbook.csv').write_bytes(gb_data)
            status,gb_summary=fetch('/admin/guestbook-summary.json',admin=True)
            assert status == 200
            (OUT / 'sample_guestbook_summary.json').write_bytes(gb_summary)
            status,csv_data=fetch('/admin/events.csv',admin=True)
            assert status == 200
            (OUT / 'sample_events.csv').write_bytes(csv_data)
            status,json_data=fetch('/admin/summary.json',admin=True)
            assert status == 200
            (OUT / 'sample_summary.json').write_bytes(json_data)
            (OUT / 'http_smoke_results.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2),encoding='utf-8')
            print('HTTP smoke test PASSED: ',len(observed),'scripted local HTTP requests')
            print(json_data.decode('utf-8'))
        finally:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
(OUT / 'README.txt').write_text('All files in this folder are LOCAL SCRIPTED SMOKE TEST RECORDS. Test guestbook labels SYNTHETIC-TEST and smoke_test.py are fabricated fixtures, NOT self-report from a real Agent. Zero real Agent trials.\n',encoding='utf-8')
