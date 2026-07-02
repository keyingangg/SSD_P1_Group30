"""Change Bid.bidder from CASCADE to SET_NULL to preserve bid history on
account deletion (PDPA / auction integrity requirement)."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0003_allow_null_draft_times"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="bid",
            name="bidder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bids",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
