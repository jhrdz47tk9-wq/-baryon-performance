"""Authenticated browser pilot. Mount behind HTTPS for remote access."""
import hmac
import json
import os
import secrets
from pathlib import Path

import psycopg
from flask import Flask, Response, abort, jsonify, render_template_string, request
from werkzeug.security import check_password_hash, generate_password_hash

from persist import save
from run import decode

FORM = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BARYON Performance</title><main><h1>Evaluar y guardar un caso sintético</h1>
<p>Revisa los controles del caso. El resultado incluye el estado y los motivos.</p>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}">
<label>Evaluación JSON<br><textarea name="payload" rows="20" cols="44" required>{{ example }}</textarea></label>
<p><button>Evaluar y guardar</button></p></form></main></html>"""


def create_app(accounts):
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
        auth = request.authorization
        account = accounts.get(auth.username) if auth and auth.type == "basic" else None
        valid = check_password_hash(account["password_hash"] if account else dummy,
                                    (auth.password or "") if auth else "")
        if not valid or not account:
            return Response(status=401, headers={"WWW-Authenticate": 'Basic realm="BARYON piloto"'})
        csrf = hmac.digest(key, auth.username.encode(), "sha256").hex()
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
        return jsonify(result)

    return app


def configured_app():
    return create_app(json.loads(Path(os.environ["BARYON_ACCOUNTS_FILE"]).read_text()))
