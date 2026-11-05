import unittest
from unittest.mock import MagicMock, patch
import test_guided_form
from pilot_web import guided_payload, HAZOP_FIELDS, CONTROLS, TIME_FIELDS
from run import execute

class GuidedHazopTests(unittest.TestCase):
    setUp = test_guided_form.GuidedFormTests.setUp
    def complete(self):
        self.values.update(hazop_enabled='yes', barrier_description='Barrera ficticia',
                           barrier_status='verified', barrier_current='yes', barrier_response='no',
                           barrier_evidence='QA-B-01 ficticia', barrier_owner='QA', action_status='none')
        self.values.update({'hazop_'+name: example for name, _, example in HAZOP_FIELDS})
        for name, _ in CONTROLS:
            self.values[name+'_status']='verified'
            self.values[name+'_evidence']='QA ficticia'
        return self.values

    def test_complete_record_only_ready_for_review(self):
        result=execute(guided_payload(self.complete()))
        self.assertEqual(result['outputs']['hazop']['status'], 'LISTO_PARA_REVISION')
        self.assertFalse(result['operational_authorization'])
        self.assertFalse(result['outputs']['hazop']['authorized'])
        self.assertEqual(result['outputs']['hazop']['nodes'][0]['record']['required_barriers'][0]['evidence_id'], 'QA-B-01 ficticia')

    def test_missing_node_information_and_failed_barrier_block(self):
        self.complete()
        for field in ('design_intent','cause','consequence'):
            values=dict(self.values, **{'hazop_'+field:''})
            h=execute(guided_payload(values))['outputs']['hazop']
            self.assertEqual(h['status'], 'NO_GO')
            self.assertIn('MISSING_'+field.upper(),h['nodes'][0]['issues'])
        self.values['barrier_status']='failed'
        self.assertEqual(execute(guided_payload(self.values))['outputs']['gate']['status'],'NO_GO')

    def test_actions_cannot_silently_disappear(self):
        self.complete()
        self.values.update(action_status='open',pending_actions='QA: acción simulada pendiente')
        result=execute(guided_payload(self.values))
        self.assertIn('OPEN_ACTIONS',result['outputs']['hazop']['nodes'][0]['issues'])
        self.assertEqual(result['outputs']['gate']['status'],'NO_GO')
        self.values['action_status']='none'
        with self.assertRaises(ValueError): guided_payload(self.values)
        self.values.update(action_status='unknown',pending_actions='')
        self.assertIn('ACTIONS_UNREVIEWED',execute(guided_payload(self.values))['outputs']['hazop']['nodes'][0]['issues'])

    def test_response_missing_zero_and_positive_margin(self):
        self.complete(); self.values['barrier_response']='yes'
        self.assertEqual(execute(guided_payload(self.values))['outputs']['gate']['status'],'NO_GO')
        self.values.update({name:'1' for name, _ in TIME_FIELDS})
        self.values['available_h']='6'
        self.assertEqual(execute(guided_payload(self.values))['outputs']['gate']['status'],'NO_GO')
        self.values['available_h']='7'
        self.assertEqual(execute(guided_payload(self.values))['outputs']['hazop']['status'],'LISTO_PARA_REVISION')
        for bad in ('nan','inf','-1','oops'):
            self.values['available_h']=bad
            with self.assertRaises(ValueError): guided_payload(self.values)

    def test_example_does_not_verify_or_authorize(self):
        response=self.client.get('/?example=hazop',headers=self.headers)
        self.assertIn('BOMBA-SIM-01',response.text)
        self.assertNotIn('value="verified" selected',response.text)
        self.assertIn('value="open" selected',response.text)

    def test_barrier_rejection_preserves_values_and_never_saves(self):
        self.complete(); self.values.update(barrier_evidence='',csrf=self.csrf,form_mode='guided',response_format='html')
        with patch('pilot_web.save') as saved, patch('pilot_web.psycopg.connect') as connect:
            response=self.client.post('/',data=self.values,headers=self.headers)
        self.assertEqual(response.status_code,422)
        self.assertIn('Agrega evidencia simulada para la barrera',response.text)
        self.assertIn('BOMBA-SIM-01',response.text)
        saved.assert_not_called(); connect.assert_not_called()

    def test_result_has_trace_and_escapes_evidence(self):
        self.complete(); self.values.update(barrier_evidence='<script>bad</script>',csrf=self.csrf,form_mode='guided',response_format='html')
        conn=MagicMock()
        conn.__enter__.return_value.execute.return_value.fetchone.return_value=('bp_pilot_app',False)
        with patch('pilot_web.psycopg.connect',return_value=conn), patch('pilot_web.save',side_effect=lambda c,p: dict(execute(p),persistence='SAVED')):
            response=self.client.post('/',data=self.values,headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertIn('LISTO_PARA_REVISION',response.text)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;',response.text)
        self.assertNotIn('<script>bad</script>',response.text)
