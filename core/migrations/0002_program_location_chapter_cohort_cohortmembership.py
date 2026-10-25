import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_default_program(apps, schema_editor):
    Program = apps.get_model("core", "Program")
    Program.objects.get_or_create(name="DREAMS", defaults={"duration_months": 36})


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[("", "Platform user"), ("admin", "Administrator")],
                default="",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Program",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "duration_months",
                    models.PositiveSmallIntegerField(
                        default=36,
                        help_text="How long each cohort runs, in months. The cohort end date is calculated from this.",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="locations",
                        to="core.program",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Chapter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chapters",
                        to="core.location",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Cohort",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chapter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cohorts",
                        to="core.chapter",
                    ),
                ),
            ],
            options={
                "ordering": ("-start_date", "name"),
            },
        ),
        migrations.CreateModel(
            name="CohortMembership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("community_leader", "Community Leader"),
                            ("mentor", "Mentor"),
                            ("mentee", "Mentee"),
                        ],
                        max_length=30,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cohort",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="core.cohort",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cohort_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("cohort__chapter__name", "cohort__name", "role"),
            },
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(
                fields=("program", "name"), name="unique_location_name_per_program"
            ),
        ),
        migrations.AddConstraint(
            model_name="chapter",
            constraint=models.UniqueConstraint(
                fields=("location", "name"), name="unique_chapter_name_per_location"
            ),
        ),
        migrations.AddConstraint(
            model_name="cohort",
            constraint=models.UniqueConstraint(
                fields=("chapter", "name"), name="unique_cohort_name_per_chapter"
            ),
        ),
        migrations.AddConstraint(
            model_name="cohortmembership",
            constraint=models.UniqueConstraint(
                fields=("user", "cohort", "role"), name="unique_user_cohort_role"
            ),
        ),
        migrations.RunPython(create_default_program, reverse_code=migrations.RunPython.noop),
    ]
