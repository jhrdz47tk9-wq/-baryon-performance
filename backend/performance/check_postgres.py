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
