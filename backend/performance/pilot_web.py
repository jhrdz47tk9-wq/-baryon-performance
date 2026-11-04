"""Authenticated browser pilot. Mount behind HTTPS for remote access."""
import hmac
import json
import os
import secrets
from urllib.parse import quote
from pathlib import Path

import jwt
import psycopg
from flask import Flask, Response, abort, jsonify, render_template_string, request
from werkzeug.security import check_password_hash, generate_password_hash

from persist import save
from run import decode

FORM = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BARYON Performance</title><main><h1>Evaluar y guardar un caso sintético</h1>
<p>Revisa los controles del caso. El resultado incluye el estado y los motivos.</p>
<form method="post"><input type="hidden" name="response_format" value="html"><input type="hidden" name="csrf" value="{{ csrf }}">
<label>Evaluación JSON<br><textarea name="payload" rows="20" cols="44" required>{{ example }}</textarea></label>
<p><button>Evaluar y guardar</button></p></form></main></html>"""


RESULT = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resultado · BARYON Performance</title>
<main>
<h1>Resultado de la evaluación</h1>
<p><strong>Prueba sintética · No autoriza una operación real.</strong></p>
<dl><dt>Caso</dt><dd>{{ result.case_id }}</dd>
<dt>Estado</dt><dd><strong>{{ gate.get('status', 'NO DISPONIBLE') }}</strong></dd>
<dt>Guardado</dt><dd>{{ 'Confirmado' if result.get('persistence') == 'SAVED' else 'No confirmado' }}</dd>
<dt>Versión del motor</dt><dd>{{ result.engine_version }}</dd></dl>
<h2>Motivos y controles pendientes</h2>
<ul>{% for reason in gate.get('reasons', []) %}
<li>{% if reason is mapping %}{{ reason.get('id', '') }}: {{ reason.get('reason', '') }}{% else %}{{ reason }}{% endif %}</li>
{% else %}<li>El motor no reportó motivos pendientes. Requiere revisión humana.</li>{% endfor %}</ul>
<p><a href="/">Volver al formulario</a> · <a download="baryon-resultado.json" href="{{ download }}">Descargar JSON</a></p>
<details><summary>Ver resultado completo</summary><pre>{{ pretty }}</pre></details>
</main></html>"""


def create_app(accounts, *, iap_audience=None, iap_users=None):
    iap_users = iap_users or {}
    if iap_audience and (not iap_users or any(v not in accounts for v in iap_users.values())):
        raise ValueError("IAP account mapping is incomplete")
    keys = jwt.PyJWKClient("https://www.gstatic.com/iap/verify/public_key-jwk", timeout=5) if iap_audience else None
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
    key = secrets.token_bytes(32)
    dummy = generate_password_hash(secrets.token_urlsafe())

    @app.after_request
    def private(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; form-action 'self'; frame-ancestors 'none'"
        return response

    @app.route("/", methods=["GET", "POST"])
    def pilot():
        if iap_audience:
            assertion = request.headers.get("X-Goog-IAP-JWT-Assertion", "")
            if not assertion:
                abort(401)
            try:
                signing_key = keys.get_signing_key_from_jwt(assertion).key
                claims = jwt.decode(
                    assertion, signing_key, algorithms=["ES256"],
                    audience=iap_audience, issuer="https://cloud.google.com/iap",
                    leeway=30, options={"require": ["exp", "iat", "aud", "iss", "sub", "email"],
                                        "strict_aud": True},
                )
                if claims["exp"] - claims["iat"] > 660 or not claims["sub"]:
                    abort(401)
            except (jwt.PyJWTError, ValueError, TypeError):
                abort(401)
            username = iap_users.get(claims["email"])
            account = accounts.get(username)
            if not account:
                abort(403)
        else:
            auth = request.authorization
            account = accounts.get(auth.username) if auth and auth.type == "basic" else None
            valid = check_password_hash(account["password_hash"] if account else dummy,
                                        (auth.password or "") if auth else "")
            if not valid or not account:
                return Response(status=401, headers={"WWW-Authenticate": 'Basic realm="BARYON piloto"'})
            username = auth.username
        csrf = hmac.digest(key, username.encode(), "sha256").hex()
        if request.method == "GET":
            example = Path(__file__).with_name("example.json").read_text()
            return render_template_string(FORM, csrf=csrf, example=example)
        if not hmac.compare_digest(request.form.get("csrf", "").encode(), csrf.encode()):
            abort(403)
        try:
            payload = decode(request.form["payload"].encode())
            if not isinstance(payload, dict) or payload.get("evidence_class") != "SYNTHETIC_TEST_ONLY":
                abort(422)
            with psycopg.connect(account["dsn"], autocommit=True, connect_timeout=5) as conn:
                role, privileged = conn.execute(
                    "SELECT rolname, rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
                ).fetchone()
                if role != account["role"] or privileged:
                    abort(503)
                result = save(conn, payload)
        except psycopg.Error:
            abort(503)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
            abort(400)
        # Browser forms opt in explicitly: the Cloud Shell forwarder does not
        # preserve Accept. Existing automated clients retain their JSON response.
        if request.form.get("response_format") == "html":
            pretty = json.dumps(result, ensure_ascii=False, indent=2)
            return render_template_string(
                RESULT, result=result, gate=result.get("outputs", {}).get("gate", {}),
                pretty=pretty, download="data:application/json;charset=utf-8," + quote(pretty),
            )
        return jsonify(result)

    return app


def configured_app():
    mode = os.environ.get("BARYON_AUTH_MODE", "basic")
    if mode not in ("basic", "iap"):
        raise ValueError("Unknown authentication mode")
    audience = os.environ["BARYON_IAP_AUDIENCE"] if mode == "iap" else None
    if mode == "iap" and not audience:
        raise ValueError("IAP audience is required")
    users = json.loads(os.environ["BARYON_IAP_USERS"]) if mode == "iap" else None
    return create_app(json.loads(Path(os.environ["BARYON_ACCOUNTS_FILE"]).read_text()),
                      iap_audience=audience, iap_users=users)
