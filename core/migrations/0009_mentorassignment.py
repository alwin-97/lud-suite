from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_termtask_termquestion_submissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cohortmembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("community_leader", "Community Leader"),
                    ("senior_member", "Senior Mentor / Member"),
                    ("mentor", "Mentor"),
                    ("mentee", "Mentee"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="MentorAssignment",
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
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Notes or goals for this mentorship pairing.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_mentor_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cohort",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mentor_assignments",
                        to="core.cohort",
                    ),
                ),
                (
                    "mentee",
                    models.ForeignKey(
                        help_text="The mentee assigned.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mentor_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "mentor",
                    models.ForeignKey(
                        help_text="The mentor assigned.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mentee_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": (
                    "cohort__name",
                    "mentor__first_name",
                    "mentee__first_name",
                ),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("cohort", "mentor", "mentee"),
                        name="unique_cohort_mentor_mentee_assignment",
                    )
                ],
            },
        ),
    ]
