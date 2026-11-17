from django.db import migrations

LEVELUP_URL = "/robot_LvUP/"
NEW_URL = "/students/evaluations/"


def apply(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    lv = MenuItem.objects.filter(url=LEVELUP_URL, parent__isnull=False).first()
    if not lv or MenuItem.objects.filter(url=NEW_URL).exists():
        return
    for m in MenuItem.objects.filter(parent=lv.parent, order__gt=lv.order):
        m.order += 1                    # 단계업관리 바로 아래에 자리를 만든다
        m.save()
    MenuItem.objects.create(
        title="평가통지서", parent=lv.parent, url=NEW_URL, icon_class="bi-file-earmark-text",
        order=lv.order + 1, access_level=lv.access_level, is_active=True,
    )


def revert(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(url=NEW_URL).delete()


class Migration(migrations.Migration):
    dependencies = [("main", "0013_seating_menu")]
    operations = [migrations.RunPython(apply, revert)]
