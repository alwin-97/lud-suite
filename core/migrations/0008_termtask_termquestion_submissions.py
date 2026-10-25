from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_useractivityreport"),
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
                    ("tasks", "Term Tasks & Submissions"),
                    ("questions", "Term Questions & Responses"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="TermTask",
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
                        help_text="Task title or milestone name.",
                        max_length=200,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text="Detailed instructions, deliverables, requirements, or prompts."
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
                        help_text="Target member format (e.g. All, Mentees, Mentors, Senior Members).",
                        max_length=30,
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        blank=True,
                        help_text="Optional submission deadline.",
                        null=True,
                    ),
                ),
                (
                    "points",
                    models.PositiveIntegerField(
                        blank=True,
                        default=100,
                        help_text="Maximum points or score.",
                        null=True,
                    ),
                ),
                (
                    "allow_text",
                    models.BooleanField(
                        default=True,
                        help_text="Accept written text or reflections.",
                    ),
                ),
                (
                    "allow_file",
                    models.BooleanField(
                        default=True,
                        help_text="Accept document file uploads (PDF, DOCX, etc.).",
                    ),
                ),
                (
                    "allow_url",
                    models.BooleanField(
                        default=True,
                        help_text="Accept external links / URLs (Google Drive, GitHub, etc.).",
                    ),
                ),
                (
                    "allow_image",
                    models.BooleanField(
                        default=True,
                        help_text="Accept image uploads (PNG, JPG, etc.).",
                    ),
                ),
                (
                    "sequence",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Order of display within the term.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        help_text="The cohort term this task belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="core.term",
                    ),
                ),
            ],
            options={
                "verbose_name": "Term task",
                "verbose_name_plural": "Term tasks",
                "ordering": ("term__sequence", "sequence", "due_date", "title"),
            },
        ),
        migrations.CreateModel(
            name="TermQuestion",
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
                        help_text="Question topic or short label.",
                        max_length=200,
                    ),
                ),
                (
                    "prompt",
                    models.TextField(
                        help_text="The question prompt, inquiry, or challenge."
                    ),
                ),
                (
                    "help_text",
                    models.TextField(
                        blank=True,
                        help_text="Guidance, hints, context, or instructions.",
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
                        help_text="Target participant category.",
                        max_length=30,
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        blank=True,
                        help_text="Optional response deadline.",
                        null=True,
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this question is mandatory.",
                    ),
                ),
                (
                    "allow_text",
                    models.BooleanField(
                        default=True,
                        help_text="Accept text responses.",
                    ),
                ),
                (
                    "allow_file",
                    models.BooleanField(
                        default=True,
                        help_text="Accept file uploads.",
                    ),
                ),
                (
                    "allow_url",
                    models.BooleanField(
                        default=True,
                        help_text="Accept external links / URLs.",
                    ),
                ),
                (
                    "allow_image",
                    models.BooleanField(
                        default=True,
                        help_text="Accept image uploads.",
                    ),
                ),
                (
                    "sequence",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Order within term.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_questions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        help_text="The cohort term this question belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="core.term",
                    ),
                ),
            ],
            options={
                "verbose_name": "Term question",
                "verbose_name_plural": "Term questions",
                "ordering": ("term__sequence", "sequence", "due_date", "title"),
            },
        ),
        migrations.CreateModel(
            name="TaskSubmission",
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
                    "text_response",
                    models.TextField(
                        blank=True,
                        help_text="Written text submission or notes.",
                    ),
                ),
                (
                    "file_submission",
                    models.FileField(
                        blank=True,
                        help_text="Document attachment (PDF, DOCX, ZIP, etc.).",
                        null=True,
                        upload_to="task_submissions/files/%Y/%m/",
                    ),
                ),
                (
                    "image_submission",
                    models.FileField(
                        blank=True,
                        help_text="Image submission (PNG, JPG, etc.).",
                        null=True,
                        upload_to="task_submissions/images/%Y/%m/",
                    ),
                ),
                (
                    "url_submission",
                    models.URLField(
                        blank=True,
                        help_text="Link / URL to external work (Google Drive, GitHub repo, live site, etc.).",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("reviewed", "Reviewed"),
                            ("approved", "Approved"),
                            ("needs_revision", "Needs Revision"),
                        ],
                        default="submitted",
                        max_length=20,
                    ),
                ),
                (
                    "score",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        help_text="Score or grade awarded (out of max points).",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "feedback",
                    models.TextField(
                        blank=True,
                        help_text="Reviewer / mentor feedback and remarks.",
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_task_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="core.termtask",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-submitted_at",),
            },
        ),
        migrations.CreateModel(
            name="QuestionResponse",
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
                    "text_response",
                    models.TextField(
                        blank=True,
                        help_text="Written answer / response.",
                    ),
                ),
                (
                    "file_submission",
                    models.FileField(
                        blank=True,
                        help_text="File attachment.",
                        null=True,
                        upload_to="question_responses/files/%Y/%m/",
                    ),
                ),
                (
                    "image_submission",
                    models.FileField(
                        blank=True,
                        help_text="Image submission.",
                        null=True,
                        upload_to="question_responses/images/%Y/%m/",
                    ),
                ),
                (
                    "url_submission",
                    models.URLField(
                        blank=True,
                        help_text="Web address / URL.",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("reviewed", "Reviewed"),
                            ("approved", "Approved"),
                        ],
                        default="submitted",
                        max_length=20,
                    ),
                ),
                (
                    "feedback",
                    models.TextField(
                        blank=True,
                        help_text="Mentor or reviewer feedback.",
                    ),
                ),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="core.termquestion",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_question_responses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="question_responses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-submitted_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="tasksubmission",
            constraint=models.UniqueConstraint(
                fields=("task", "user"),
                name="unique_user_task_submission",
            ),
        ),
        migrations.AddConstraint(
            model_name="questionresponse",
            constraint=models.UniqueConstraint(
                fields=("question", "user"),
                name="unique_user_question_response",
            ),
        ),
    ]
