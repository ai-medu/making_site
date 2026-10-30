from django.db import migrations


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    parent = MenuItem.objects.filter(title="관리", parent__isnull=True).first()
    if not parent:
        return
    MenuItem.objects.get_or_create(
        title="회원정지", url="/accounts/suspended_users/", parent=parent,
        defaults={"order": 2, "access_level": "staff", "is_active": True},
    )


def remove_menu(apps, schema_editor):
    apps.get_model("main", "MenuItem").objects.filter(url="/accounts/suspended_users/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_profile_suspend_adminseen"),
        ("main", "0010_aiapikey_openrouter"),
    ]
    operations = [migrations.RunPython(add_menu, remove_menu)]
