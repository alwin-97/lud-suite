from django.db import migrations


def backfill_roles(apps, schema_editor):
    CustomUser = apps.get_model('core', 'CustomUser')
    for user in CustomUser.objects.all():
        if user.role and not user.roles:
            user.roles = [user.role]
            user.save(update_fields=['roles'])


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_repositoryasset_evidenceattachment'),
    ]

    operations = [
        migrations.RunPython(backfill_roles, reverse_backfill),
    ]
