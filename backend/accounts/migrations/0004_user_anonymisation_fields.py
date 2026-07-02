"""Add is_anonymised and anonymised_at to User for PDPA soft-delete support."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_accountlockoutprofile_usersessionrecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_anonymised",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="anonymised_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
