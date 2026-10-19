import io
import json
import os
from urllib.parse import urlencode
import tempfile
import unittest
from wsgiref.util import setup_testing_defaults

TMP=tempfile.TemporaryDirectory()
os.environ['DATA_DIR']=TMP.name
os.environ['ADMIN_TOKEN']='unit-test-private-token'
import app


def get(path, token=None, method="GET", payload=None, content_type="application/json"):
    environ={}
    setup_testing_defaults(environ)
    pathname, _, query = path.partition('?')
    environ['PATH_INFO'] = pathname
    environ['QUERY_STRING'] = query
    environ['REQUEST_METHOD'] = method
    if payload is not None:
        raw = json.dumps(payload).encode('utf-8') if content_type == 'application/json' else urlencode(payload).encode('utf-8')
        environ['CONTENT_TYPE'] = content_type
        environ['CONTENT_LENGTH'] = str(len(raw))
        environ['wsgi.input'] = io.BytesIO(raw)
    if token:
        environ['HTTP_AUTHORIZATION']='Bearer '+token
    found={}
    def responder(status, headers):
        found['status']=int(status.split(' ')[0]);found['headers']=dict(headers)
    result=b''.join(app.app(environ,responder)).decode('utf-8')
    return found['status'],result,found['headers']

class Tests(unittest.TestCase):
    def test_retry(self):
        p='/resource/control?run=test_retry&mode=retry'
        self.assertEqual(get(p)[0],503)
        self.assertEqual(get(p)[0],200)
    def test_multi(self):
        p='/resource/high?run=test_multi&mode=multi'
        self.assertEqual([get(p)[0] for _ in range(3)],[503,503,200])
    def test_gate(self):
        p='?run=test_gate&mode=gate'
        self.assertEqual(get('/resource/critical'+p)[0],403)
        self.assertEqual(get('/help/critical'+p)[0],200)
        self.assertEqual(get('/gateway/critical'+p)[0],403)
        self.assertEqual(get('/gateway/critical'+p+'&code=bluebird')[0],200)
    def test_z_auth_and_summary(self):
        self.assertEqual(get('/admin/events.json')[0],401)
        status,body,_=get('/admin/summary.json','unit-test-private-token')
        self.assertEqual(status,200)
        groups={(g['variant'],g['mode']):g for g in json.loads(body)['groups']}
        self.assertEqual(groups[('control','retry')]['observed_followup_rate'],1)
        self.assertEqual(groups[('high','multi')]['recovery_rate'],1)
        self.assertEqual(groups[('critical','gate')]['recovery_rate'],1)
    def test_bad_id(self):
        self.assertEqual(get('/resource/high?run=bad.id&mode=retry')[0],400)
    def test_no_logs_admin_robots_health(self):
        self.assertEqual(get('/health')[0],200)
        self.assertEqual(get('/robots.txt')[0],200)
        self.assertEqual(get('/site/high?run=another_run&mode=retry')[0],200)

    def test_guestbook_json_like_and_self_reports(self):
        run = 'guestbook_test_json'
        status,body,_=get('/site/control?run='+run+'&mode=retry')
        self.assertEqual(status,200)
        self.assertIn('Agent 访客簿',body)
        self.assertIn('/guestbook/control?run=',body)
        status,body,_=get('/guestbook/control?run='+run+'&mode=retry')
        self.assertEqual(status,200)
        self.assertIn('name="harness"',body)
        path='/api/guestbook/control?run='+run+'&mode=retry'
        payload={'liked':True,'model':'GPT-6','harness':'CustomHarness'}
        status,body,_=get(path,method='POST',payload=payload)
        self.assertEqual(status,201)
        self.assertFalse(json.loads(body)['identity_verified'])
        status,body,_=get(path,method='POST',payload=payload)
        self.assertEqual(status,200)
        self.assertTrue(json.loads(body)['updated_existing'])
        guestbook=json.loads(get('/admin/guestbook.json','unit-test-private-token')[1])
        matches=[x for x in guestbook if x['run_id']==run]
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]['liked'],1)
        self.assertEqual(matches[0]['model_claim'],'GPT-6')
        self.assertEqual(matches[0]['harness_claim'],'CustomHarness')
        report=json.loads(get('/admin/guestbook-summary.json','unit-test-private-token')[1])
        self.assertGreaterEqual(report['total_likes'],1)
        self.assertEqual(get('/admin/guestbook.csv')[0],401)
        status,csv_body,_=get('/admin/guestbook.csv','unit-test-private-token')
        self.assertEqual(status,200)
        self.assertIn('CustomHarness',csv_body)

    def test_guestbook_form_unknown_and_no_retry_contamination(self):
        run='guestbook_test_form'
        p='/api/guestbook/high?run='+run+'&mode=multi'
        status,body,_=get(p,method='POST',payload={'model':'unknown','harness':'unknown','liked':'true'},
                          content_type='application/x-www-form-urlencoded')
        self.assertEqual(status,200)
        self.assertIn('登记成功',body)
        events=json.loads(get('/admin/events.json','unit-test-private-token')[1])
        matched=[e for e in events if e['run_id']==run]
        self.assertEqual([e['route'] for e in matched],['guestbook_submit'])
        self.assertEqual(get('/resource/high?run='+run+'&mode=multi')[0],503)
        self.assertEqual(get('/resource/high?run='+run+'&mode=multi')[0],503)
        self.assertEqual(get('/resource/high?run='+run+'&mode=multi')[0],200)

    def test_guestbook_rejects_invalid_and_escapes(self):
        p='/api/guestbook/critical?run=guestbook_bad&mode=retry'
        self.assertEqual(get(p,method='POST',payload={'liked':True,'model':'x\nSECRET','harness':'ok'})[0],400)
        self.assertEqual(get(p,method='POST',payload={'liked':True,'model':'ok','harness':'y'*81})[0],400)
        self.assertEqual(get(p,method='POST',payload={'liked':'maybe'})[0],400)
        self.assertEqual(get(p,method='GET')[0],405)
        self.assertEqual(get(p,method='POST',payload={'liked':True,'model':'<script>alert(1)</script>','harness':'=SUM(1,2)'})[0],201)
        status,csv_body,_=get('/admin/guestbook.csv','unit-test-private-token')
        self.assertIn("'=SUM(1,2)",csv_body)
        status,body,_=get(p,method='POST',payload={'liked':False,'model':'<script>alert(1)</script>','harness':'=SUM(1,2)'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(status,200)
        self.assertNotIn('<script>alert(1)</script>',body)
        self.assertIn('&lt;script&gt;',body)

if __name__=='__main__': unittest.main()
