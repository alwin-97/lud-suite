from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_senior_member_and_cohort_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="RolePermission",
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
                            ("senior_member", "Senior Member"),
                            ("mentor", "Mentor"),
                            ("mentee", "Mentee"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "resource",
                    models.CharField(
                        choices=[
                            ("terms", "Cohort Terms"),
                            ("resources", "Term Resources (Files & URLs)"),
                            ("activities", "Cohort Activities & Timeline"),
                            ("members", "Member Allocation & Reallocation"),
                            ("cohorts", "Cohorts & Structure"),
                            ("audit_log", "Audit Trail & Logs"),
                        ],
                        max_length=30,
                    ),
                ),
                ("can_create", models.BooleanField(default=False)),
                ("can_read", models.BooleanField(default=True)),
                ("can_update", models.BooleanField(default=False)),
                ("can_delete", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("role", "resource"),
            },
        ),
        migrations.AddConstraint(
            model_name="rolepermission",
            constraint=models.UniqueConstraint(
                fields=("role", "resource"),
                name="unique_role_resource_permission",
            ),
        ),
    ]
