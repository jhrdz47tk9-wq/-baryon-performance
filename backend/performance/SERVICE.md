# Local synthetic API — 0.5 candidate

This standard-library HTTP harness is for local integration tests only. It binds
127.0.0.1 and refuses startup in a Cloud Run K_SERVICE environment. It does not
provide production TLS, user identity, tenant authorization, durable audit or storage.

From the repository root, in one terminal:

```sh
export BARYON_LOCAL_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 backend/performance/server.py
```

Set the same token in the caller environment without committing or logging it.
POST /v1/performance/run requires Authorization: Bearer <token>, Content-Type:
application/json and Content-Length. The body uses the existing example.json or
hazop_example.json format and must declare SYNTHETIC_TEST_ONLY. This declaration
is a caller assertion, not proof of data origin. Maximum body size: 1 MiB.
The CLI also accepts UNVALIDATED_CASE; this HTTP harness does not.

GET /healthz reports liveness without authentication and does not validate a case.
HTTP 200 means evaluation completed; inspect the returned gate status. NO_GO can
be returned with HTTP 200. All results remain NOT_SAVED and do not authorize operation.

Errors: 400 invalid JSON/input or transfer encoding; 401 missing/invalid token;
403 browser Origin supplied; 404 unknown route; 408 body timeout; 411 missing or
invalid Content-Length; 413 oversized body; 415 wrong media type; 422 non-synthetic
case. Duplicate JSON keys and nonfinite numbers are rejected. Browser-origin
requests are rejected; no CORS integration is provided. Request logging is disabled.

Verification:

```sh
python3 -m unittest discover -s backend/performance -v
```

The 67-test suite includes actual loopback HTTP requests, rejected credentials,
malformed input, body limits, case restrictions, propagation of NO_GO, and autonomy
margin regressions. It does not establish production security or cloud readiness.

Before a remote service: implement managed identity and authorization, production
HTTP hosting, registered Performance context, transactional persistence, real
PostgreSQL RLS/concurrency verification, and frontend integration.

### Interfaz autenticada del piloto
Desde backend/performance, instala requirements-pilot.txt. Aprovisiona pilot.sql
en una base de prueba y concede a cada rol LOGIN solo USAGE en performance_pilot
y SELECT, INSERT en runs. Usa un rol sin membresías privilegiadas por cliente.
Configura BARYON_ACCOUNTS_FILE con la ruta de un archivo JSON privado de solo
lectura para el servicio. Cada clave es un usuario individual y su valor contiene
password_hash (werkzeug.security.generate_password_hash), role (rol PostgreSQL)
y dsn (conexión de ese rol). Guarda este archivo fuera del repositorio.
Ejecuta gunicorn --workers 1 --bind 127.0.0.1:8080 'pilot_web:configured_app()'
y abre http://127.0.0.1:8080/. Para acceso remoto, termina HTTPS en un proxy
autorizado. El formulario usa autenticación HTTP Basic y acepta casos sintéticos.
