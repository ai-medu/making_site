from django.db import migrations


def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")

    parent = MenuItem.objects.filter(title="이력", parent__isnull=True).first()
    if not parent:
        return

    if MenuItem.objects.filter(title="학력관리", parent=parent).exists():
        return

    career = MenuItem.objects.filter(title__startswith="경력관리", parent=parent).first()
    order = career.order if career else 35

    MenuItem.objects.create(
        title="학력관리",
        parent=parent,
        url="/teachers/educations/",
        order=order,
        access_level="teacher",
    )


def remove_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(title="학력관리", url="/teachers/educations/").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_add_nuribom_hub_menu"),
    ]

    operations = [
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
