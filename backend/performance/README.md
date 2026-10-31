# Performance pilot engine 0.5 candidate

Runs locally with Python 3.12 standard library. The CLI has no network, credentials or database dependency. The optional local HTTP harness uses a local token.

```sh
python3 -m unittest discover -s backend/performance -v
python3 backend/performance/run.py < backend/performance/example.json
```

Input schema `baryon-performance/0.3` requires case_id, evidence_class and controls.
Each control has a unique id, critical boolean and verified boolean or null.
Only SYNTHETIC_TEST_ONLY and UNVALIDATED_CASE inputs are accepted. These labels do not verify origin.
Optional autonomy, oee, error_tree and economics objects use the keyword arguments of the corresponding functions.
The adapter validates supplied fields; it cannot establish that the control inventory is complete.

Economic bridge: one reconciled consequence per consequence_id, baseline and scenario
amounts, source_id, shared currency, period and constant price_basis. Contribution margin
changes are scenario minus baseline; incremental operating costs are baseline minus scenario.
Gross revenue and CAPEX are excluded. Decimal arithmetic preserves monetary precision.
Missing amounts/evidence yield an unavailable total. Duplicate IDs are rejected.
Different IDs describing the same physical loss require upstream reconciliation; the engine cannot infer it.
This is an incremental bridge, not total company EBITDA or accounting certification.

NO_GO remains active even when economic benefit is positive. No result authorizes operation.
Input hashes are deterministic trace identifiers, not a persistence or retry guarantee.
Output explicitly says NOT_SAVED and NOT_EXECUTED for plant validation.

BP2-MOTOR-003: adds economic bridge, JSON executable adapter, integration tests and CI.
38 local tests passed: 23 carried forward plus 15 economic/adapter checks.
No simulated probabilities are represented as calibrated THERP or NASA values.

Open gaps: full dependency-aware THERP/PRA, calibration, production HTTP service,
identity/tenant authorization, transactional persistence, deployment and frontend connection.
The separately reviewed Assembly 05 PostgreSQL candidate is scoped to one FPC/Sherlock
synthetic case and must not be wired directly to this pilot. Its SQL transport tests use mocks,
not a real PostgreSQL server. Do not change its case/model IDs to claim compatibility.
Next integration requires a registered Performance model/test context and PostgreSQL tests
with real schema/role, RLS isolation, concurrent retry and commit/readback.
No production migrations, credentials, historical records or UI changes are included.

## HAZOP extension
See HAZOP.md and hazop_example.json. Engine output is now 0.4. Schema 0.3 remains accepted with incomplete HAZOP flagged. Current suite: 67 tests. Engine version is 0.5-candidate; output schema remains 0.4.


## Local service and autonomy correction
BP2-SERVICE-005: see SERVICE.md for the loopback-only synthetic HTTP harness.
Exhausted containment time or two insufficient response margins now yield NO_GO.
Missing margins, changed conditions, or one insufficient response margin require
review of the response plan; a feasible alternative does not automatically clear it.
Existing NO_GO decisions remain active. These outputs never authorize plant operation.
