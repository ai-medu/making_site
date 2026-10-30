from django.db import migrations


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    parent = MenuItem.objects.filter(title="모집", parent__isnull=True).first()
    if not parent:
        return
    MenuItem.objects.get_or_create(
        title="출강강사모집", url="/recruit/dispatch/", parent=parent,
        defaults={"order": 12, "access_level": "teacher", "is_active": True, "icon_class": "bi-person-workspace"},
    )


def remove_menu(apps, schema_editor):
    apps.get_model("main", "MenuItem").objects.filter(url="/recruit/dispatch/").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("recruit", "0021_dispatchrecruit"),
        ("main", "0011_hide_institution_menu"),
    ]
    operations = [migrations.RunPython(add_menu, remove_menu)]
