BEGIN;
CREATE SCHEMA performance_pilot;
CREATE TABLE performance_pilot.runs (
    tenant_role name NOT NULL DEFAULT current_user,
    engine_version text NOT NULL,
    input_hash text NOT NULL,
    result jsonb NOT NULL,
    PRIMARY KEY (tenant_role, engine_version, input_hash)
);
ALTER TABLE performance_pilot.runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_pilot.runs FORCE ROW LEVEL SECURITY;
CREATE POLICY own_runs ON performance_pilot.runs
    USING (tenant_role = current_user) WITH CHECK (tenant_role = current_user);
COMMIT;
