import unittest
from unittest.mock import patch, MagicMock
import test_guided_hazop
from pilot_web import guided_payload, TRACE_FIELDS
from run import execute

class DocumentTraceTests(unittest.TestCase):
    setUp = test_guided_hazop.GuidedHazopTests.setUp
    complete = test_guided_hazop.GuidedHazopTests.complete

    def test_trace_preserved_and_changes_fingerprint(self):
        self.complete()
        first = execute(guided_payload(self.values))
        self.assertEqual(first['context']['evidence_trace']['competence']['document'], 'QA ficticia: document')
        barrier = first['outputs']['hazop']['nodes'][0]['record']['required_barriers'][0]
        self.assertEqual(barrier['document_trace']['reviewer'], 'QA ficticia: reviewer')
        self.values['competence_trace_document'] = 'Otro documento ficticio v2'
        second = execute(guided_payload(self.values))
        self.assertNotEqual(first['input_sha256'], second['input_sha256'])
        self.assertFalse(second['operational_authorization'])

    def test_each_missing_verified_trace_field_rejected(self):
        self.complete()
        for prefix in ('competence', 'barrier'):
            for key, _ in TRACE_FIELDS:
                with self.subTest(prefix=prefix, key=key):
                    with self.assertRaises(ValueError):
                        guided_payload(dict(self.values, **{prefix+'_trace_'+key:' '}))

    def test_json_validation_and_legacy_compatibility(self):
        self.complete(); payload = guided_payload(self.values)
        payload['context']['evidence_trace']['competence']['observed'] = ''
        with self.assertRaises(ValueError): execute(payload)
        del payload['context']['evidence_trace']
        del payload['hazop'][0]['required_barriers'][0]['document_trace']
        self.assertEqual(execute(payload)['outputs']['gate']['status'], 'LISTO_PARA_REVISION')

    def test_invalid_trace_keeps_form_and_never_connects(self):
        self.complete(); self.values.update(competence_trace_reviewer='', csrf=self.csrf, form_mode='guided', response_format='html')
        with patch('pilot_web.psycopg.connect') as connect:
            response=self.client.post('/',data=self.values,headers=self.headers)
        self.assertEqual(response.status_code,422)
        self.assertIn('Completa la trazabilidad documental',response.text)
        self.assertIn('QA ficticia: document',response.text)
        connect.assert_not_called()

    def test_trace_rendered_and_escaped(self):
        self.complete(); self.values.update(competence_trace_document='<script>trace</script>',csrf=self.csrf,form_mode='guided',response_format='html')
        conn=MagicMock()
        conn.__enter__.return_value.execute.return_value.fetchone.return_value=('bp_pilot_app',False)
        with patch('pilot_web.psycopg.connect',return_value=conn), patch('pilot_web.save',side_effect=lambda c,p:dict(execute(p),persistence='SAVED')):
            response=self.client.post('/',data=self.values,headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertIn('&lt;script&gt;trace&lt;/script&gt;',response.text)
        self.assertNotIn('<script>trace</script>',response.text)
        self.assertIn('Revisor declarado',response.text)
