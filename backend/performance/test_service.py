import unittest,threading,http.client,json
from server import create_server
from run import execute
class ServiceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.token='x'*40;cls.server=create_server(cls.token);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def payload(self):return dict(schema='baryon-performance/0.4',case_id='TEST',evidence_class='SYNTHETIC_TEST_ONLY',controls=[],hazop=[])
 def request(self,body=None,headers=None,path='/v1/performance/run',method='POST'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
  h={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'};h.update(headers or {})
  c.request(method,path,body=json.dumps(self.payload()) if body is None else body,headers=h);r=c.getresponse();code=r.status;data=json.loads(r.read());c.close();return code,data
 def test_http_roundtrip(self):
  code,r=self.request();self.assertEqual(code,200);self.assertEqual(r['outputs']['gate']['status'],'PENDIENTE');self.assertFalse(r['operational_authorization'])
 def test_wrong_token(self):self.assertEqual(self.request(headers={'Authorization':'Bearer wrong'})[0],401)
 def test_health(self):self.assertEqual(self.request(method='GET',path='/healthz')[0],200)
 def test_route(self):self.assertEqual(self.request(path='/unknown')[0],404)
 def test_origin(self):self.assertEqual(self.request(headers={'Origin':'https://example.com'})[0],403)
 def test_media(self):self.assertEqual(self.request(headers={'Content-Type':'text/plain'})[0],415)
 def test_malformed(self):self.assertEqual(self.request(body='{')[0],400)
 def test_duplicates(self):self.assertEqual(self.request(body='{"a":1,"a":2}')[0],400)
 def test_large(self):self.assertEqual(self.request(body='{}',headers={'Content-Length':'1048577'})[0],413)
 def test_real_case_rejected(self):
  p=self.payload();p['evidence_class']='UNVALIDATED_CASE';self.assertEqual(self.request(body=json.dumps(p))[0],422)
 def test_no_go(self):
  p=self.payload();p['controls']=[dict(id='a',critical=True,verified=False)];self.assertEqual(self.request(body=json.dumps(p))[1]['outputs']['gate']['status'],'NO_GO')
 def test_weak_token(self):
  with self.assertRaises(ValueError):create_server('weak')
 def test_autonomy_exhausted(self):
  p=self.payload();p['autonomy']=dict(initial_h=8,elapsed_h=8,unchanged=True);self.assertEqual(execute(p)['outputs']['gate']['status'],'NO_GO')
 def test_both_margins(self):
  p=self.payload();p['autonomy']=dict(initial_h=8,elapsed_h=6,unchanged=True,recovery_h=2,mitigation_h=2,reserve_h=1);self.assertEqual(execute(p)['outputs']['gate']['status'],'NO_GO')
 def test_alternative_requires_review(self):
  p=self.payload();p['autonomy']=dict(initial_h=8,elapsed_h=6,unchanged=True,recovery_h=3,mitigation_h=.5,reserve_h=.5)
  r=execute(p);self.assertEqual(r['outputs']['gate']['status'],'PENDIENTE');self.assertIn({'id':'autonomy','reason':'REVIEW_RESPONSE_PLAN'},r['outputs']['gate']['reasons'])
if __name__=='__main__':unittest.main()
