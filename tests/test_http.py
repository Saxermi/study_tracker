"""Full local HTTP handler integration tests without external Python dependencies."""
from __future__ import annotations
import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import TestCase, mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

class HTTPTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_patch = mock.patch.object(server,'DATA_DIR',Path(self.tmp.name)/'data')
        self.backup_patch = mock.patch.object(server,'BACKUP_DIR',Path(self.tmp.name)/'backup')
        self.data_patch.start();self.backup_patch.start()
        server.SESSIONS.clear()
        self.http = ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.port = self.http.server_port
        self.thread = threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join(4)
        self.data_patch.stop();self.backup_patch.stop()
        server.SESSIONS.clear();self.tmp.cleanup()

    def request(self,path,method='GET',body=None,client=None,origin=None):
        hdr={}
        if body is not None:
            hdr['Content-Type']='application/json'
        if origin:
            hdr['Origin']=origin
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', method=method,
            data=json.dumps(body).encode() if body is not None else None, headers=hdr)
        opener=client or self.client
        try:
            with opener.open(req) as r:
                raw=r.read()
                return r.status, json.loads(raw.decode()) if 'json' in r.headers.get('Content-Type','') else raw
        except urllib.error.HTTPError as e:
            raw=e.read()
            return e.code,json.loads(raw.decode()) if raw else {}

    def login_admin(self):
        s,data=self.request('/api/auth/setup','POST',{'display_name':'Alex','username':'alex','password':'very-secure-password'})
        self.assertEqual(s,200)
        return data

    def test_auth_and_data_isolation(self):
        st, info=self.request('/api/auth/status')
        self.assertTrue(info['setup_required'])
        self.assertEqual(self.request('/api/state')[0],401)
        self.login_admin()
        self.assertEqual(self.request('/api/state')[0],200)
        self.assertEqual(self.request('/api/users')[0],200)
        st, u2=self.request('/api/users','POST',{'display_name':'Sam','username':'sam','password':'sam-password-1234'})
        self.assertEqual(st,200)
        st, task=self.request('/api/tasks','POST',{'title':'Meine Aufgabe','subject_id':'mathe','planned_minutes':60})
        self.assertEqual(st,200)
        self.assertEqual(len(task['state']['tasks']),1)
        other=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.assertEqual(self.request('/api/state',client=other)[0],401)
        self.assertEqual(self.request('/api/auth/login','POST',{'username':'sam','password':'sam-password-1234'},client=other)[0],200)
        st, state2=self.request('/api/state',client=other)
        self.assertEqual(state2['state']['tasks'],[])
        self.assertEqual(self.request('/api/users',client=other)[0],403)
        self.assertEqual(self.request('/api/users','POST',{'display_name':'X','username':'something','password':'strong-password'},client=other)[0],403)

    def test_exports_task_import_and_csrf(self):
        self.login_admin()
        self.assertEqual(self.request('/api/import/tasks','POST',{'format':'studytracker.tasks.v1','batch_id':'mail-1','tasks':[{'external_id':'mail-1:1','subject':'Mathematik','title':'Kapitel lesen','planned_minutes':40} ]})[0],200)
        status,backup=self.request('/api/export?format=json')
        self.assertEqual(status,200)
        parsed=backup if isinstance(backup,dict) else json.loads(backup)
        self.assertEqual(parsed['data']['tasks'][0]['title'],'Kapitel lesen')
        status,csv=self.request('/api/export?format=csv&kind=tasks')
        self.assertEqual(status,200)
        self.assertIn(b'40',csv)
        self.assertEqual(self.request('/api/settings','PATCH',{'weekly_goal_minutes':60},origin='http://attacker.invalid')[0],403)
        self.assertEqual(self.request('/api/import/backup','POST',parsed)[0],200)

if __name__=='__main__':
    import unittest
    unittest.main()
