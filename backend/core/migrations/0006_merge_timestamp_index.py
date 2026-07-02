from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_auditlog_timestamp_index"),
        ("core", "0005_audit_allow_pii_scrubbing"),
    ]

    operations = []
