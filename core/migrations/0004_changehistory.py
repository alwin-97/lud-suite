import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_term_termresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChangeHistory",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Created"),
                            ("update", "Updated"),
                            ("delete", "Deleted"),
                            ("activate", "Activated"),
                            ("deactivate", "Deactivated"),
                            ("upload", "Uploaded"),
                            ("remove", "Removed"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        help_text="e.g. Program, Location, Chapter, Cohort, Term, Resource, Member, User",
                        max_length=50,
                    ),
                ),
                ("entity_id", models.PositiveIntegerField(blank=True, null=True)),
                ("entity_name", models.CharField(max_length=255)),
                (
                    "description",
                    models.TextField(help_text="Human-readable summary of the change."),
                ),
                (
                    "details",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Structured details or field-level differences.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        help_text="The user who performed the change.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="performed_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cohort",
                    models.ForeignKey(
                        blank=True,
                        help_text="Associated cohort if applicable.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="change_history",
                        to="core.cohort",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Change histories",
                "ordering": ("-created_at",),
            },
        ),
    ]
