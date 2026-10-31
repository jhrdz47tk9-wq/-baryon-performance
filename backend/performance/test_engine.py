import unittest
from datetime import datetime, timezone, timedelta
from engine import *
class PilotTests(unittest.TestCase):
 def test_changed_conditions(self):
  self.assertIsNone(autonomy(8,2,False,3,1,1)['remaining_h'])
 def test_missing_not_zero(self):
  self.assertIsNone(autonomy(8,None,True)['remaining_h'])
 def test_distinct_margins(self):
  r=autonomy(8,2,True,6,2,1); self.assertEqual(r['recovery_margin_h'],-1); self.assertEqual(r['mitigation_margin_h'],3)
 def test_zero_margin(self): self.assertEqual(autonomy(8,2,True,5,1,1)['recovery_margin_h'],0)
 def test_negative_remaining(self): self.assertEqual(autonomy(8,9,True)['remaining_h'],-1)
 def test_critical_unknown(self): self.assertEqual(gate([dict(id='competence',critical=True,verified=None)])['status'],'NO_GO')
 def test_never_authorizes(self): self.assertFalse(gate([dict(id='technical',critical=True,verified=True)])['authorized'])
 def test_operational_acceptance(self): self.assertEqual(gate([dict(id='technical',critical=True,verified=True),dict(id='operational',critical=True,verified=None)])['status'],'NO_GO')
 def test_rejection_persists(self): self.assertEqual(evidence(applicable=True,identity=True,criteria=[False,None]),'DESVIACION')
 def test_unverified_rejection(self): self.assertEqual(evidence(applicable=True,identity=False,criteria=[False]),'SIN_RESPALDO')
 def test_exact_deadline(self):
  t=datetime.now(timezone.utc); self.assertEqual(evidence(applicable=True,identity=True,criteria=[True],due=t,received=t),'CONFORME')
 def test_late(self):
  t=datetime.now(timezone.utc); self.assertEqual(evidence(applicable=True,identity=True,criteria=[True],due=t,received=t+timedelta(seconds=1)),'DESVIACION')
 def test_no_denominator(self): self.assertIsNone(coverage([])['coverage'])
 def test_coverage(self):
  r=coverage(['CONFORME','SIN_RESPALDO','APLICABILIDAD_PENDIENTE']); self.assertEqual(r['coverage'],.5); self.assertEqual(r['unresolved_applicability'],1)
 def test_balance(self): self.assertEqual(balance(20,100,[dict(hours=10,in_m3_h=10,out_m3_h=0)])['hours'],8)
 def test_changed_inflow(self): self.assertEqual(balance(20,100,[dict(hours=2,in_m3_h=10,out_m3_h=0),dict(hours=5,in_m3_h=20,out_m3_h=0)])['hours'],5)
 def test_empty(self): self.assertEqual(balance(20,100,[dict(hours=3,in_m3_h=0,out_m3_h=10)])['hours'],2)
 def test_probability(self):
  r=error_tree(.1,.8,.75); self.assertAlmostEqual(r['unresolved'],.04); self.assertAlmostEqual(sum(r[k] for k in ('initial_success','undetected','recovered','detected_unresolved')),1)
 def test_probability_missing(self): self.assertIsNone(error_tree(None,.5,.5))
 def test_invalid(self):
  for x in (-1,float('nan'),float('inf'),True,1.1):
   with self.assertRaises(ValueError): error_tree(x,.5,.5)
 def test_oee(self): self.assertAlmostEqual(oee(10,8,10,64,60)['oee'],.6)
 def test_oee_missing(self): self.assertIsNone(oee(10,0,10,0,0))
 def test_duplicate_controls(self):
  with self.assertRaises(ValueError): gate([dict(id='a',critical=True,verified=True)]*2)
if __name__=='__main__': unittest.main(verbosity=2)
