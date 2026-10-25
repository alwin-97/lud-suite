import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_changehistory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cohortmembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("community_leader", "Community Leader"),
                    ("senior_member", "Senior Member"),
                    ("mentor", "Mentor"),
                    ("mentee", "Mentee"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="changehistory",
            name="action",
            field=models.CharField(
                choices=[
                    ("create", "Created"),
                    ("update", "Updated"),
                    ("delete", "Deleted"),
                    ("allocate", "Allocated"),
                    ("reallocate", "Reallocated"),
                    ("activate", "Activated"),
                    ("deactivate", "Deactivated"),
                    ("upload", "Uploaded"),
                    ("remove", "Removed"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="CohortActivity",
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
                        help_text="Activity or milestone title.", max_length=200
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Objectives, deliverables, or agenda."
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("delayed", "Delayed"),
                        ],
                        default="planned",
                        max_length=20,
                    ),
                ),
                (
                    "target_audience",
                    models.CharField(
                        choices=[
                            ("all", "All Cohort Members"),
                            ("senior_members", "Senior Members"),
                            ("mentors", "Mentors"),
                            ("mentees", "Mentees"),
                            ("community_leaders", "Community Leaders"),
                        ],
                        default="all",
                        help_text="Member format/category participating in this activity.",
                        max_length=30,
                    ),
                ),
                (
                    "sequence",
                    models.PositiveSmallIntegerField(
                        default=1, help_text="Sequence order within the term."
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cohort",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="core.cohort",
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        help_text="The term this activity is scheduled in.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="core.term",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Cohort activities",
                "ordering": ("term__sequence", "sequence", "start_date", "title"),
            },
        ),
    ]
