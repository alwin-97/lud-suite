from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_rolepermission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rolepermission",
            name="resource",
            field=models.CharField(
                choices=[
                    ("terms", "Cohort Terms"),
                    ("resources", "Term Resources (Files & URLs)"),
                    ("activities", "Cohort Activities & Timeline"),
                    ("members", "Member Allocation & Reallocation"),
                    ("cohorts", "Cohorts & Structure"),
                    ("audit_log", "Audit Trail & Logs"),
                    ("reports", "User Activity Reports"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="UserActivityReport",
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
                        help_text="Report title or activity summary heading.",
                        max_length=200,
                    ),
                ),
                (
                    "report_date",
                    models.DateField(
                        default=django.utils.timezone.now,
                        help_text="Date of reporting or activity completion.",
                    ),
                ),
                (
                    "hours_spent",
                    models.DecimalField(
                        decimal_places=1,
                        default=0.0,
                        help_text="Hours invested in this activity/period.",
                        max_digits=5,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("reviewed", "Reviewed"),
                            ("approved", "Approved"),
                        ],
                        default="submitted",
                        max_length=20,
                    ),
                ),
                (
                    "progress_status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("delayed", "Delayed"),
                        ],
                        default="completed",
                        help_text="Milestone or task progress outcome.",
                        max_length=20,
                    ),
                ),
                (
                    "summary",
                    models.TextField(
                        help_text="Summary of activities performed, deliverables completed, or achievements."
                    ),
                ),
                (
                    "reflections",
                    models.TextField(
                        blank=True,
                        help_text="Learnings, key takeaways, personal growth, and mentorship insights.",
                    ),
                ),
                (
                    "challenges",
                    models.TextField(
                        blank=True,
                        help_text="Obstacles or roadblocks encountered and how they were resolved.",
                    ),
                ),
                (
                    "next_steps",
                    models.TextField(
                        blank=True,
                        help_text="Planned goals, commitments, and action items for the upcoming term/period.",
                    ),
                ),
                (
                    "attachment",
                    models.FileField(
                        blank=True,
                        help_text="Supporting evidence, photos, presentations, work files, or documentation.",
                        null=True,
                        upload_to="activity_reports/%Y/%m/",
                    ),
                ),
                (
                    "feedback",
                    models.TextField(
                        blank=True,
                        help_text="Reviewer or leader feedback and evaluation notes.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "activity",
                    models.ForeignKey(
                        blank=True,
                        help_text="Specific planned cohort activity or milestone, if applicable.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="user_reports",
                        to="core.cohortactivity",
                    ),
                ),
                (
                    "cohort",
                    models.ForeignKey(
                        help_text="The cohort in which these activities took place.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_reports",
                        to="core.cohort",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_activity_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional term context.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="user_activity_reports",
                        to="core.term",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The participant whose activities are being reported.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User activity report",
                "verbose_name_plural": "User activity reports",
                "ordering": ("-report_date", "-created_at"),
            },
        ),
    ]
