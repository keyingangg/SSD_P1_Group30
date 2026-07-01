"""Allow the narrow PDPA PII-scrubbing UPDATE on audit_logs (NFSR-C-08).

The trigger previously blocked ALL UPDATE statements unconditionally.
This migration replaces the function with one that permits exactly one
pattern: zeroing ip_address / user_agent / device_fingerprint / row_hash
while leaving every other column unchanged. All other UPDATEs and all
DELETEs continue to be rejected.
"""
from django.db import migrations

RELAXED_TRIGGER = r"""
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS trigger AS $$
BEGIN
    -- Block all DELETEs unconditionally.
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_logs is append-only';
        RETURN NULL;
    END IF;

    -- Allow the narrow PDPA PII-scrubbing UPDATE (NFSR-C-08 / SFR-05c):
    -- only ip_address, user_agent, device_fingerprint, and row_hash may
    -- change, and only to the fixed anonymisation sentinel values.
    IF (
        NEW.id                 = OLD.id
        AND NEW.user_id        IS NOT DISTINCT FROM OLD.user_id
        AND NEW.action         = OLD.action
        AND NEW.resource_type  = OLD.resource_type
        AND NEW.resource_id    IS NOT DISTINCT FROM OLD.resource_id
        AND NEW.timestamp      = OLD.timestamp
        AND NEW.ip_address     IS NULL
        AND NEW.user_agent     = ''
        AND NEW.device_fingerprint = ''
        AND NEW.row_hash       = '[PII_ANONYMISED]'
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'audit_logs is append-only';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

STRICT_TRIGGER = r"""
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_auditlog_user_fk_no_constraint"),
    ]

    operations = [
        migrations.RunSQL(RELAXED_TRIGGER, reverse_sql=STRICT_TRIGGER),
    ]
