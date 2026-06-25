from django.db import migrations, models


def migrate_closed_to_ended(apps, schema_editor):
    Listing = apps.get_model("auctions", "Listing")
    Listing.objects.filter(status="closed").update(status="ended")


class Migration(migrations.Migration):

    dependencies = [
        ("auctions", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE listings "
                        "ADD COLUMN IF NOT EXISTS category varchar(50) "
                        "NOT NULL DEFAULT 'Others';"
                    ),
                    reverse_sql="ALTER TABLE listings DROP COLUMN IF EXISTS category;",
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="listing",
                    name="category",
                    field=models.CharField(
                        choices=[
                            ("Handbag", "Handbag"),
                            ("Watches", "Watches"),
                            ("Perfumes", "Perfumes"),
                            ("Fashion & Apparel", "Fashion & Apparel"),
                            ("Accessories", "Accessories"),
                            ("Fine Art & Collectibles", "Fine Art & Collectibles"),
                            ("Wines & Spirits", "Wines & Spirits"),
                            ("Home Decor & Furniture", "Home Decor & Furniture"),
                            ("Others", "Others"),
                        ],
                        default="Others",
                        max_length=50,
                    ),
                )
            ],
        ),
        migrations.AlterField(
            model_name="listing",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("scheduled", "Scheduled"),
                    ("active", "Active"),
                    ("ended", "Ended"),
                    ("cancelled", "Cancelled"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_closed_to_ended, migrations.RunPython.noop),
    ]
