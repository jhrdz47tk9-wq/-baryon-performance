"""Run against a fresh disposable database as its administrator."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg

from persist import save

directory = Path(__file__).parent
dsn = os.environ["DATABASE_URL"]
payload = json.loads((directory / "example.json").read_text())
with psycopg.connect(dsn, autocommit=True) as admin:
    admin.execute((directory / "pilot.sql").read_text())
    admin.execute("CREATE ROLE pilot_a")
    admin.execute("CREATE ROLE pilot_b")
    admin.execute("GRANT USAGE ON SCHEMA performance_pilot TO pilot_a, pilot_b")
    admin.execute("GRANT SELECT, INSERT ON performance_pilot.runs TO pilot_a, pilot_b")


def retry(_):
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET ROLE pilot_a")
        return save(conn, payload)


with ThreadPoolExecutor(4) as pool:
    results = list(pool.map(retry, range(8)))
assert all(result == results[0] for result in results)
assert results[0]["outputs"]["gate"]["status"] == "NO_GO"
with psycopg.connect(dsn, autocommit=True) as conn:
    conn.execute("SET ROLE pilot_b")
    assert conn.execute("SELECT count(*) FROM performance_pilot.runs").fetchone() == (0,)
    save(conn, payload)
    conn.execute("RESET ROLE")
    assert conn.execute("SELECT count(*) FROM performance_pilot.runs").fetchone() == (2,)

# Authenticate through the actual HTML form and confirm the assigned login owns the row.
from psycopg.conninfo import make_conninfo
from werkzeug.security import generate_password_hash
from pilot_web import create_app
import re
import secrets

password = secrets.token_hex(24)
with psycopg.connect(dsn, autocommit=True) as admin:
    admin.execute(psycopg.sql.SQL("ALTER ROLE pilot_a LOGIN PASSWORD {}").format(psycopg.sql.Literal(password)))
account = {"role": "pilot_a", "dsn": make_conninfo(dsn, user="pilot_a", password=password),
           "password_hash": generate_password_hash(password)}
client = create_app({"operator": account}).test_client()
assert client.get("/").status_code == 401
auth = ("operator", password)
page = client.get("/", auth=auth)
csrf = re.search(rb'name="csrf" value="([a-f0-9]+)"', page.data)[1].decode()
payload["case_id"] = "SYNTHETIC_BROWSER"
form = {"payload": json.dumps(payload)}
assert client.post("/", data=form, auth=auth).status_code == 403
form["csrf"] = csrf
response = client.post("/", data=form, auth=auth)
assert response.status_code == 200
assert response.json["persistence"] == "SAVED"
assert response.json["outputs"]["gate"]["status"] == "NO_GO"
with psycopg.connect(dsn) as admin:
    assert admin.execute("SELECT tenant_role FROM performance_pilot.runs WHERE result->>'case_id'=%s",
                         (payload["case_id"],)).fetchall() == [("pilot_a",)]
