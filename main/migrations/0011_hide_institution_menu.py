from django.db import migrations


def hide(apps, schema_editor):
    # 기관 모집은 더 이상 하지 않으므로 상단 '기관' 메뉴를 숨김(삭제하지 않음 - 메뉴관리에서 다시 켤 수 있음)
    apps.get_model("main", "MenuItem").objects.filter(
        title="기관", parent__isnull=True, access_level="institution").update(is_active=False)


def show(apps, schema_editor):
    apps.get_model("main", "MenuItem").objects.filter(
        title="기관", parent__isnull=True, access_level="institution").update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("main", "0010_aiapikey_openrouter")]
    operations = [migrations.RunPython(hide, show)]
