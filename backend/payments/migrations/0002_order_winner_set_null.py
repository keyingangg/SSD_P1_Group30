"""Change Order.winner from CASCADE to SET_NULL to preserve payment records
on account deletion (PDPA / auction integrity requirement)."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="winner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
