import unittest
import re
import base64
from unittest.mock import MagicMock, patch
from werkzeug.security import generate_password_hash
from pilot_web import create_app, guided_payload, CONTROLS, TRACE_FIELDS
from run import execute

class GuidedFormTests(unittest.TestCase):
    def setUp(self):
        self.values = {"case_id":"SIM-001", "task":"Reparación simulada", "responsible":"Persona de prueba"}
        for prefix in [name for name, _ in CONTROLS] + ['barrier']:
            self.values.update({prefix+'_trace_'+key: 'QA ficticia: '+key for key, _ in TRACE_FIELDS})
        self.client = create_app({"test":{"password_hash":generate_password_hash("test"),
                                          "dsn":"unused", "role":"bp_pilot_app"}}).test_client()
        self.headers = {"Authorization":"Basic "+base64.b64encode(b"test:test").decode()}
        self.html = self.client.get("/", headers=self.headers).text
        self.csrf = re.search(r'name="csrf" value="([^"]+)"', self.html)[1]

    def test_defaults_block_and_no_invented_economics(self):
        p = guided_payload(self.values)
        r = execute(p)
        self.assertEqual(r["outputs"]["gate"]["status"], "NO_GO")
        self.assertEqual(len(r["outputs"]["gate"]["reasons"]), 4)
        self.assertNotIn("economics", r["outputs"])
        self.assertEqual(r["context"]["task"], self.values["task"])
        self.assertNotIn('name="payload"', self.html)

    def test_evidence_required_and_hazop_pending(self):
        for id, _ in CONTROLS:
            self.values[id+"_status"] = "verified"
        with self.assertRaises(ValueError):
            guided_payload(self.values)
        for id, _ in CONTROLS:
            self.values[id+"_evidence"] = "Documento ficticio"
        r = execute(guided_payload(self.values))
        self.assertEqual(r["outputs"]["gate"]["status"], "PENDIENTE")
        self.assertFalse(r["operational_authorization"])
        self.values["competence_status"] = "failed"
        self.assertEqual(execute(guided_payload(self.values))["outputs"]["gate"]["status"], "NO_GO")

    def test_post_persists_context_and_renders_spanish(self):
        conn = MagicMock()
        conn.__enter__.return_value.execute.return_value.fetchone.return_value = ("bp_pilot_app", False)
        def save(_, payload):
            result = execute(payload)
            result["persistence"] = "SAVED"
            return result
        self.values.update(csrf=self.csrf, form_mode="guided", response_format="html")
        with patch("pilot_web.psycopg.connect", return_value=conn), patch("pilot_web.save", side_effect=save) as saved:
            r = self.client.post("/", data=self.values, headers=self.headers)
            self.assertEqual(r.status_code, 200)
            self.assertIn("Sin verificar", r.text)
            self.assertIn("Confirmado", r.text)
            self.assertEqual(saved.call_args.args[1]["context"]["responsible"], "Persona de prueba")
            self.values["competence_status"] = "verified"
            r = self.client.post("/", data=self.values, headers=self.headers)
            self.assertEqual(r.status_code, 422)
            self.assertIn("Reparación simulada", r.text)
            self.assertEqual(saved.call_count, 1)

    def test_input_rejection(self):
        for bad in ("yes", "true", "bypass"):
            with self.assertRaises(ValueError):
                guided_payload(dict(self.values, competence_status=bad))
        with self.assertRaises(ValueError):
            guided_payload(dict(self.values, case_id=""))
        with self.assertRaises(ValueError):
            guided_payload(dict(self.values, task="x"*501))

if __name__ == "__main__":
    unittest.main()
