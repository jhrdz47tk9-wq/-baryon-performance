import unittest,json,subprocess,sys
from pathlib import Path
from economics import bridge
from run import execute
ROOT=Path(__file__).parent
class Integration(unittest.TestCase):
 def row(self,**kw):
  return dict(consequence_id='c1',kind='incremental_opex',currency='USD',period='TEST_PERIOD',price_basis='CONSTANT_TEST',source_id='SYNTHETIC',baseline='100',scenario='20',**kw)
 def calc(self,rows):return bridge(rows,currency='USD',period='TEST_PERIOD',price_basis='CONSTANT_TEST')
 def payload(self):return {'schema':'baryon-performance/0.3','case_id':'TEST','evidence_class':'SYNTHETIC_TEST_ONLY','controls':[{'id':'competence','critical':True,'verified':None}]}
 def test_saved_cost(self):self.assertEqual(self.calc([self.row()])['delta_ebitda'],'80')
 def test_margin(self):
  r=self.row();r.update(kind='contribution_margin',scenario='150');self.assertEqual(self.calc([r])['delta_ebitda'],'50')
 def test_duplicate(self):
  with self.assertRaises(ValueError):self.calc([self.row(),self.row()])
 def test_gross_revenue_rejected(self):
  r=self.row();r['kind']='revenue'
  with self.assertRaises(ValueError):self.calc([r])
 def test_capex_rejected(self):
  r=self.row();r['kind']='capex'
  with self.assertRaises(ValueError):self.calc([r])
 def test_missing(self):
  r=self.row();r['scenario']=None;self.assertIsNone(self.calc([r])['delta_ebitda'])
 def test_no_evidence(self):
  r=self.row();r['source_id']='';self.assertIsNone(self.calc([r])['delta_ebitda'])
 def test_currency(self):
  r=self.row();r['currency']='CLP'
  with self.assertRaises(ValueError):self.calc([r])
 def test_exact_decimal(self):
  r=self.row();r.update(baseline='0.3',scenario='0.1');self.assertEqual(self.calc([r])['delta_ebitda'],'0.2')
 def test_hash(self):self.assertEqual(execute(self.payload()),execute(dict(reversed(list(self.payload().items())))))
 def test_no_go_with_profit(self):
  p=self.payload();p['economics']=dict(entries=[self.row()],currency='USD',period='TEST_PERIOD',price_basis='CONSTANT_TEST')
  r=execute(p);self.assertEqual(r['outputs']['gate']['status'],'NO_GO');self.assertFalse(r['operational_authorization'])
 def test_cli(self):
  r=subprocess.run([sys.executable,str(ROOT/'run.py')],input=json.dumps(self.payload()),text=True,capture_output=True)
  self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['persistence'],'NOT_SAVED')
 def test_cli_duplicate_keys(self):
  r=subprocess.run([sys.executable,str(ROOT/'run.py')],input='{"schema":1,"schema":2}',text=True,capture_output=True);self.assertEqual(r.returncode,2)
 def test_bad_version(self):
  p=self.payload();p['schema']='future'
  with self.assertRaises(ValueError):execute(p)
 def test_empty_controls(self):
  p=self.payload();p['controls']=[];self.assertEqual(execute(p)['outputs']['gate']['status'],'PENDIENTE')
if __name__=='__main__':unittest.main()
