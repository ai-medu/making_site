from django.db import migrations

STUDENT_URL = "/students/list/"
NEW_URL = "/seating/"


def apply(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    stu = MenuItem.objects.filter(url=STUDENT_URL, parent__isnull=False).first()
    if not stu or MenuItem.objects.filter(url=NEW_URL).exists():
        return
    for m in MenuItem.objects.filter(parent=stu.parent, order__gt=stu.order):
        m.order += 1                    # 학생관리 바로 아래에 자리를 만든다
        m.save()
    MenuItem.objects.create(
        title="자리관리", parent=stu.parent, url=NEW_URL, icon_class="bi-grid-3x3-gap",
        order=stu.order + 1, access_level=stu.access_level, is_active=True,
    )


def revert(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(url=NEW_URL).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0012_program_register_menu")]
    operations = [migrations.RunPython(apply, revert)]
