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

CONTROLS = [
    ("competence", "Competencia de la persona"),
    ("risk_assessment", "Análisis de riesgos de la tarea"),
    ("energy_isolation", "Aislamiento de energías"),
    ("environment", "Protección ambiental y de terceros"),
]
REASONS = {"UNVERIFIED": "Sin verificar", "FAILED": "No cumple",
           "ASSESSMENT_INCOMPLETE": "Análisis de riesgos incompleto",
           "CRITICAL_PROTECTION_GAP": "Falta una protección crítica",
           "NO_CONTROLS": "No se registraron controles"}
LABELS = dict(CONTROLS, hazop="HAZOP")

FORM = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BARYON Performance</title><main><h1>Evaluar un caso de prueba</h1>
<p><strong>Prueba sintética · No autoriza una operación real.</strong></p>
<p>Completa una tarea simulada. Los cuatro controles son críticos y esta lista no sustituye el análisis completo de riesgos.</p>
{% if error %}<p role="alert"><strong>{{ error }}</strong></p>{% endif %}
<form method="post">
<input type="hidden" name="form_mode" value="guided">
<input type="hidden" name="response_format" value="html">
<input type="hidden" name="csrf" value="{{ csrf }}">
<p><label>Código del caso<br><input name="case_id" maxlength="120" required value="{{ values.get('case_id', 'PILOTO_SIMULADO_001') }}"></label></p>
<p><label>Tarea simulada<br><input name="task" maxlength="500" required value="{{ values.get('task', '') }}"></label></p>
<p><label>Responsable del caso simulado<br><input name="responsible" maxlength="200" required value="{{ values.get('responsible', '') }}"></label></p>
{% for id, label in controls %}
<fieldset><legend>{{ label }} · Crítico</legend>
<p><label>Estado<br><select name="{{ id }}_status">
{% for code, text in [('unknown','Sin verificar'), ('failed','No cumple'), ('verified','Verificado en la simulación')] %}
<option value="{{ code }}" {% if values.get(id ~ '_status', 'unknown') == code %}selected{% endif %}>{{ text }}</option>
{% endfor %}</select></label></p>
<p><label>Referencia o descripción de evidencia simulada<br>
<textarea name="{{ id }}_evidence" rows="3" cols="36" maxlength="1000">{{ values.get(id ~ '_evidence', '') }}</textarea></label></p>
<p>Para marcar verificado debes indicar una referencia. El sistema registra tu declaración; no valida el documento.</p>
</fieldset>
{% endfor %}
<p>El HAZOP completo permanece pendiente. Completar estos controles no habilita una operación.</p>
<button type="submit">Evaluar y guardar</button></form></main></html>"""


def guided_payload(form):
    def field(name, limit):
        value = form.get(name, "").strip()
        if len(value) > limit:
            raise ValueError("Un campo supera la longitud permitida.")
        return value
    case = field("case_id", 120)
    context = {"task": field("task", 500), "responsible": field("responsible", 200)}
    if not case or not all(context.values()):
        raise ValueError("Completa el código, la tarea y el responsable.")
    controls = []
    evidence = {}
    for id, label in CONTROLS:
        status = form.get(id + "_status", "unknown")
        if status not in ("unknown", "failed", "verified"):
            raise ValueError("Estado de control inválido.")
        reference = field(id + "_evidence", 1000)
        if status == "verified" and not reference:
            raise ValueError("Agrega evidencia simulada para: " + label + ".")
        controls.append({"id": id, "critical": True,
                         "verified": {"unknown": None, "failed": False, "verified": True}[status]})
        evidence[id] = reference
    context["evidence"] = evidence
    return {"schema": "baryon-performance/0.4", "case_id": case,
            "evidence_class": "SYNTHETIC_TEST_ONLY", "controls": controls,
            "hazop": [], "context": context}


RESULT = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resultado · BARYON Performance</title>
<main>
<h1>Resultado de la evaluación</h1>
<p><strong>Prueba sintética · No autoriza una operación real.</strong></p>
<dl><dt>Caso</dt><dd>{{ result.case_id }}</dd>
{% if result.get('context') %}<dt>Tarea simulada</dt><dd>{{ result.context.task }}</dd>
<dt>Responsable</dt><dd>{{ result.context.responsible }}</dd>{% endif %}
<dt>Estado</dt><dd><strong>{{ gate.get('status', 'NO DISPONIBLE') }}</strong></dd>
<dt>Guardado</dt><dd>{{ 'Confirmado' if result.get('persistence') == 'SAVED' else 'No confirmado' }}</dd>
<dt>Versión del motor</dt><dd>{{ result.engine_version }}</dd></dl>
<h2>Motivos y controles pendientes</h2>
<ul>{% for reason in gate.get('reasons', []) %}
<li>{% if reason is mapping %}{{ labels.get(reason.get('id'), reason.get('id', '')) }}: {{ reasons.get(reason.get('reason'), reason.get('reason', '')) }}{% else %}{{ reasons.get(reason, reason) }}{% endif %}</li>
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
            return render_template_string(FORM, csrf=csrf, values={}, controls=CONTROLS)
        if not hmac.compare_digest(request.form.get("csrf", "").encode(), csrf.encode()):
            abort(403)
        try:
            if request.form.get("form_mode") == "guided":
                try:
                    payload = guided_payload(request.form)
                except ValueError as exc:
                    return render_template_string(FORM, csrf=csrf, values=request.form,
                                                  controls=CONTROLS, error=str(exc)), 422
            else:
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
                RESULT, result=result, labels=LABELS, reasons=REASONS, gate=result.get("outputs", {}).get("gate", {}),
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
