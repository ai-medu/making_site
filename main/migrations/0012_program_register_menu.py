from django.db import migrations

OLD_URL = "/teachers/nuribom-hub/"
NEW_URL = "/teachers/program-register/"


def apply(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    hub = MenuItem.objects.filter(url=OLD_URL, parent__isnull=False).first()
    if not hub:
        return
    hub.title = "늘봄허브서류"          # 기존 '늘봄허브등록'(강사 제출 서류) → 이름 변경
    hub.save()
    if MenuItem.objects.filter(url=NEW_URL).exists():
        return
    for m in MenuItem.objects.filter(parent=hub.parent, order__gt=hub.order):
        m.order += 1                    # 바로 아래에 자리를 만든다
        m.save()
    MenuItem.objects.create(
        title="늘봄허브등록", parent=hub.parent, url=NEW_URL, icon_class="bi-megaphone",
        order=hub.order + 1, access_level=hub.access_level, is_active=True,
    )


def revert(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(url=NEW_URL).delete()
    MenuItem.objects.filter(url=OLD_URL).update(title="늘봄허브등록")


class Migration(migrations.Migration):
    dependencies = [("main", "0011_hide_institution_menu")]
    operations = [migrations.RunPython(apply, revert)]
