from django.db import migrations


SQL = r"""
-- Prevent accidental or malicious UPDATE/DELETE on audit_logs table.
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_audit_update_delete ON audit_logs;
CREATE TRIGGER prevent_audit_update_delete
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- Revoke non-essential privileges from PUBLIC as a first step.
REVOKE UPDATE, DELETE ON TABLE audit_logs FROM PUBLIC;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
