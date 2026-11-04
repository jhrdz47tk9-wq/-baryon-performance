import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from pilot_web import create_app

class IAPTests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.aud = "/projects/123456789/locations/test-region/services/test-service"
        self.app = create_app({"alvaro": {"role": "bp_pilot_app"}}, iap_audience=self.aud,
                              iap_users={"alvaro@example.com": "alvaro"})
        self.client = self.app.test_client()

    def call(self, changes=None, key=None):
        now = int(time.time())
        claims = dict(iss="https://cloud.google.com/iap", aud=self.aud,
                      sub="user-123", email="alvaro@example.com", iat=now, exp=now+600)
        claims.update(changes or {})
        token = jwt.encode(claims, key or self.key, algorithm="ES256", headers={"kid":"test"})
        with patch("jwt.PyJWKClient.get_signing_key_from_jwt",
                   return_value=SimpleNamespace(key=self.key.public_key())):
            return self.client.get("/", headers={"X-Goog-IAP-JWT-Assertion":token})

    def test_valid(self):
        self.assertEqual(self.call().status_code, 200)

    def test_invalid(self):
        for changes in ({"aud":"other"}, {"iss":"other"}, {"exp":1},
                        {"iat":int(time.time())+120}, {"exp":int(time.time())+900}):
            with self.subTest(changes=changes):
                self.assertEqual(self.call(changes).status_code, 401)
        self.assertEqual(self.call(key=ec.generate_private_key(ec.SECP256R1())).status_code, 401)

    def test_other_user(self):
        self.assertEqual(self.call({"email":"other@example.com"}).status_code, 403)

    def test_no_header_or_basic_fallback(self):
        r = self.client.get("/", headers={"Authorization":"Basic YWx2YXJvOnBhc3M=",
                                          "X-Goog-Authenticated-User-Email":"accounts.google.com:alvaro@example.com"})
        self.assertEqual(r.status_code,401)
        self.assertNotIn("WWW-Authenticate", r.headers)

if __name__ == "__main__":
    unittest.main()
