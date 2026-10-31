"""Persist a synthetic evaluation using a trusted database role per tenant."""
import os
import sys

import psycopg
from psycopg.types.json import Jsonb

from run import canonical, decode, execute


def save(connection, payload):
    if payload.get("evidence_class") != "SYNTHETIC_TEST_ONLY":
        raise ValueError("synthetic cases only")
    result = execute(payload)
    canonical(result)
    result["persistence"] = "SAVED"
    with connection.transaction():
        record = connection.execute(
            """INSERT INTO performance_pilot.runs (engine_version, input_hash, result)
               VALUES (%s, %s, %s)
               ON CONFLICT (tenant_role, engine_version, input_hash) DO NOTHING
               RETURNING result""",
            (result["engine_version"], result["input_sha256"], Jsonb(result)),
        ).fetchone()
        if record is None:
            record = connection.execute(
                """SELECT result FROM performance_pilot.runs
                   WHERE tenant_role = current_user AND engine_version = %s AND input_hash = %s""",
                (result["engine_version"], result["input_sha256"]),
            ).fetchone()
    return record[0]


if __name__ == "__main__":
    payload = decode(sys.stdin.buffer.read(1048577))
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as connection:
        print(canonical(save(connection, payload)))
