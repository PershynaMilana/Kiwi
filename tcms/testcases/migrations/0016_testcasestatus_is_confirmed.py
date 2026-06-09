from django.db import migrations, models


def forwards(apps, schema_editor):
    test_case_status_model = apps.get_model("testcases", "TestCaseStatus")
    for status in test_case_status_model.objects.all():
        if status.name == "CONFIRMED":
            status.is_confirmed = True
            status.save()


class Migration(migrations.Migration):
    dependencies = [
        ("testcases", "0015_add_summary_db_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcasestatus",
            name="is_confirmed",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
