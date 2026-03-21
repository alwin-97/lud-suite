from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_alter_customuser_role_alter_diaryentry_review_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="VolunteerReportingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="volunteer_reporting_assignments_created", to=settings.AUTH_USER_MODEL)),
                ("endorser", models.ForeignKey(limit_choices_to={"role": "endorser"}, on_delete=django.db.models.deletion.PROTECT, related_name="volunteer_reporting_assignments", to=settings.AUTH_USER_MODEL)),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="volunteer_reporting_assignments", to="core.location")),
                ("programme", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="volunteer_reporting_assignments", to="core.programme")),
                ("volunteer", models.OneToOneField(limit_choices_to={"role": "volunteer"}, on_delete=django.db.models.deletion.CASCADE, related_name="reporting_assignment", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["volunteer__first_name", "volunteer__username"],
            },
        ),
    ]
