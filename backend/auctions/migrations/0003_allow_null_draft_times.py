from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0002_listing_category_and_status_update"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="starts_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="listing",
            name="ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
