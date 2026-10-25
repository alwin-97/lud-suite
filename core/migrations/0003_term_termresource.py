import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_program_location_chapter_cohort_cohortmembership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Term",
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
                (
                    "sequence",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Sequence order of this term within the cohort (e.g. 1 for Term 1).",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cohort",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="terms",
                        to="core.cohort",
                    ),
                ),
            ],
            options={
                "ordering": ("sequence", "start_date", "name"),
            },
        ),
        migrations.CreateModel(
            name="TermResource",
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
                    "title",
                    models.CharField(
                        help_text="Display title for this resource.", max_length=200
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("document", "Document"),
                            ("image", "Image"),
                            ("link", "Link / URL"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        blank=True, null=True, upload_to="terms/resources/"
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        blank=True,
                        help_text="Web address / external link (e.g. https://...)",
                        max_length=500,
                        null=True,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "term",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resources",
                        to="core.term",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="term",
            constraint=models.UniqueConstraint(
                fields=("cohort", "name"), name="unique_term_name_per_cohort"
            ),
        ),
    ]
