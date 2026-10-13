import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def assign_existing_locations_to_dreams(apps, schema_editor):
    Program = apps.get_model("core", "Program")
    Location = apps.get_model("core", "Location")
    dreams, _ = Program.objects.get_or_create(
        name="DREAMS",
        defaults={"duration_months": 36},
    )
    Location.objects.filter(program__isnull=True).update(program=dreams)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_chapter_location_alter_customuser_role_cohort_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Program",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                ("duration_months", models.PositiveSmallIntegerField(default=36, help_text="How long each cohort runs, in months. The cohort end date is calculated from this.", validators=[django.core.validators.MinValueValidator(1)])),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddField(
            model_name="location",
            name="program",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="locations", to="core.program"),
        ),
        migrations.RunPython(assign_existing_locations_to_dreams, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="location",
            name="program",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="locations", to="core.program"),
        ),
        migrations.AlterField(
            model_name="location",
            name="name",
            field=models.CharField(max_length=150),
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(fields=("program", "name"), name="unique_location_name_per_program"),
        ),
    ]
