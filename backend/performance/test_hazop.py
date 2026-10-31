import unittest
from hazop import evaluate
from run import execute
class HazopTests(unittest.TestCase):
 def node(self):
  return dict(id='N1',critical=True,design_intent='Transfer liquid',parameter='flow',guideword='NO',deviation='No flow',cause='Pump unavailable',consequence='Containment exhausted',owner='TEST',activity_id='TEST-E06',required_barriers=[dict(id='alarm_response',verified=True,current=True,evidence_id='SYNTHETIC',owner='TEST',response_required=True,detection_h=.1,decision_h=.1,mobilization_h=.2,execution_h=.3,effect_h=.3,reserve_h=1,available_h=3)])
 def test_verified_margin(self):
  r=evaluate([self.node()]);self.assertEqual(r['status'],'LISTO_PARA_REVISION');self.assertEqual(r['nodes'][0]['barriers'][0]['margin_h'],1);self.assertFalse(r['authorized'])
 def test_alarm_not_enough(self):
  n=self.node();n['required_barriers'][0]['verified']=None;self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_stale(self):
  n=self.node();n['required_barriers'][0]['current']=False;self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_missing_evidence(self):
  n=self.node();n['required_barriers'][0]['evidence_id']='';self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_zero_margin(self):
  n=self.node();n['required_barriers'][0]['available_h']=2;self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_negative_margin(self):
  n=self.node();n['required_barriers'][0]['available_h']=1;self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_effect_not_instant(self):
  n=self.node();n['required_barriers'][0]['effect_h']=None;self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_no_barriers(self):
  n=self.node();n['required_barriers']=[];self.assertEqual(evaluate([n])['status'],'NO_GO')
 def test_empty(self):self.assertEqual(evaluate([])['status'],'PENDIENTE')
 def test_duplicate(self):
  with self.assertRaises(ValueError):evaluate([self.node(),self.node()])
 def test_unknown_criticality(self):
  n=self.node();n['critical']=None;self.assertEqual(evaluate([n])['status'],'PENDIENTE')
 def test_integration(self):
  n=self.node();n['required_barriers']=[]
  p=dict(schema='baryon-performance/0.4',case_id='TEST',evidence_class='SYNTHETIC_TEST_ONLY',controls=[dict(id='competence',critical=True,verified=True)],hazop=[n])
  self.assertEqual(execute(p)['outputs']['gate']['status'],'NO_GO')
 def test_legacy_incomplete(self):
  p=dict(schema='baryon-performance/0.3',case_id='TEST',evidence_class='SYNTHETIC_TEST_ONLY',controls=[dict(id='competence',critical=True,verified=True)])
  self.assertEqual(execute(p)['outputs']['gate']['status'],'PENDIENTE')
 def test_v4_requires_hazop(self):
  with self.assertRaises(ValueError):execute(dict(schema='baryon-performance/0.4',case_id='TEST',evidence_class='SYNTHETIC_TEST_ONLY',controls=[]))
if __name__=='__main__':unittest.main()
