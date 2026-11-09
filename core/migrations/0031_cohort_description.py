from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_alter_rolepermission_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="cohort",
            name="description",
            field=models.TextField(blank=True, max_length=500),
        ),
    ]
