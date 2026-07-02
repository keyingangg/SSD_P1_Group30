import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_payment_record(apps, schema_editor):
    """Populate amount/currency/listing on pre-existing orders so every payment
    row is a self-contained financial record (FSR-AC-10). amount comes from the
    winning bid, currency from the configured Stripe currency, listing from the
    winning bid's listing. IP/session stay null (unknown for historical rows)."""
    Order = apps.get_model("payments", "Order")
    currency = getattr(settings, "STRIPE_CURRENCY", "sgd")
    for order in Order.objects.select_related("winning_bid").all():
        order.amount = order.winning_bid.amount
        order.currency = currency
        order.listing_id = order.winning_bid.listing_id
        order.save(update_fields=["amount", "currency", "listing"])


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0003_allow_null_draft_times'),
        ('payments', '0002_order_winner_set_null'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='currency',
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='listing',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='auctions.listing'),
        ),
        migrations.AddField(
            model_name='order',
            name='session_id',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.RunPython(backfill_payment_record, migrations.RunPython.noop),
    ]
