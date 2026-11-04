#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
BP_DIR=$(cat "$HOME/.baryon-install-path")
BP_BUILD=$(mktemp -d "$BP_DIR/readable-build.XXXXXX")
BP_BASE=https://raw.githubusercontent.com/jhrdz47tk9-wq/-baryon-performance/6484ded20e417ab187fca2dd77ceaad503cc4707/backend/performance
for BP_FILE in Dockerfile requirements-pilot.txt persist.py run.py engine.py economics.py hazop.py example.json; do
  curl -fsSL "$BP_BASE/$BP_FILE" -o "$BP_BUILD/$BP_FILE"
done
cat > "$BP_BUILD/pilot_web.py" <<'BARYON_PY'
"""Authenticated browser pilot. Mount behind HTTPS for remote access."""
import hmac
import json
import os
import secrets
from urllib.parse import quote
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
    return create_app(json.loads(Path(os.environ["BARYON_ACCOUNTS_FILE"]).read_text()))

BARYON_PY
chmod 644 "$BP_BUILD/"*
python3 -m py_compile "$BP_BUILD/pilot_web.py"
gcloud run services describe baryon-performance-pilot --project=paragonia-ark-dev --region=southamerica-west1 --format=json > "$BP_DIR/before-readable-ui.json"
gcloud run deploy baryon-performance-pilot --project=paragonia-ark-dev --region=southamerica-west1 --source="$BP_BUILD" --no-allow-unauthenticated --quiet
gcloud run services describe baryon-performance-pilot --project=paragonia-ark-dev --region=southamerica-west1 --format='yaml(status.latestReadyRevisionName,status.conditions,status.url)'
printf '\nActualización terminada. Recarga el formulario antes de evaluar.\n'
