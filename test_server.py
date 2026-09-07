"""Real loopback requests, isolated local data, and controller access disabled."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import server


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=patch.object(server,'DATA',Path(self.temp.name));self.data.start();self.addCleanup(self.data.stop)
        self.service=server.start(0,True)
        self.addCleanup(self.service.server_close);self.addCleanup(self.service.shutdown)
    def request(self,path,headers=None,body=None):
        data=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(self.service.origin+path,data=data,headers=headers or {})
        try:
            with urllib.request.urlopen(req) as response:return response.status,response.read()
        except urllib.error.HTTPError as e:
            with e:return e.code,e.read()
    def test_token_and_origin_required(self):
        self.assertEqual(self.request('/api/status')[0],403)
        headers={'X-ODP-Token':self.service.token}
        self.assertEqual(self.request('/api/status',headers)[0],200)
        self.assertEqual(self.request('/api/status',headers|{'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(self.request('/session.js',{'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.request('/session.js',{'Sec-Fetch-Site':'same-site'})[0],403)
    def test_draft_is_saved_outside_browser_origin(self):
        from test_planner import mission
        headers={'X-ODP-Token':self.service.token}
        self.assertEqual(self.request('/api/draft',headers,{'mission':mission()})[0],200)
        code,body=self.request('/api/draft',headers)
        self.assertEqual(code,200);self.assertIsInstance(json.loads(body),dict);self.assertEqual(json.loads(body)['name'],mission()['name'])
        self.assertEqual(json.loads((Path(self.temp.name)/'draft.json').read_text())['home'],[-121,39])
    def test_library_identity_survives_saved_project_id(self):
        from test_planner import mission
        headers={'X-ODP-Token':self.service.token};value=mission();value['id']='a'*32
        code,_=self.request('/api/save',headers,{'id':'b'*32,'value':value})
        self.assertEqual(code,200)
        code,body=self.request('/api/library',headers)
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['missions'][0]['id'],'b'*32)
    def test_bad_host_and_traversal(self):
        self.assertEqual(self.request('/api/status',{'Host':'attacker.invalid','X-ODP-Token':self.service.token})[0],403)
        self.assertEqual(self.request('/../../server.py')[0],404)
    def test_offline_blocks_controller_mutation(self):
        with self.assertRaisesRegex(ValueError,'disabled'):self.service.usb(lambda:None)
        self.assertEqual(self.request('/api/reset-slot',{'X-ODP-Token':self.service.token},{} )[0],400)

if __name__=='__main__':unittest.main()
