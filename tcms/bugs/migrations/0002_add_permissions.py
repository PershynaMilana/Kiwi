from django.db import migrations


def forwards_add_perms(apps, schema_editor):
    """
    Adds permissions for this app to the group 'Tester'.
    This is useful in case that is an existing installation
    upgrading post 7.0.
    """
    group_model = apps.get_model("auth", "Group")
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")

    tester = group_model.objects.get(name="Tester")
    ct_ids = list(
        content_type_model.objects.filter(app_label="bugs").values_list("pk", flat=True)
    )
    if ct_ids:
        app_perms = list(permission_model.objects.filter(content_type_id__in=ct_ids))
        tester.permissions.add(*app_perms)


def backwards(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    permission_model = apps.get_model("auth", "Permission")
    content_type_model = apps.get_model("contenttypes", "ContentType")

    tester = group_model.objects.get(name="Tester")
    ct_ids = list(
        content_type_model.objects.filter(app_label="bugs").values_list("pk", flat=True)
    )
    if ct_ids:
        app_perms = list(permission_model.objects.filter(content_type_id__in=ct_ids))
        tester.permissions.remove(*app_perms)


class Migration(migrations.Migration):
    dependencies = [
        ("bugs", "0001_initial"),
        ("core", "0001_squashed"),
    ]

    operations = [
        migrations.RunPython(forwards_add_perms, backwards),
    ]
