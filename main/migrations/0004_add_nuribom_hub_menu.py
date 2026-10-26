from django.db import migrations


def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")

    parent = MenuItem.objects.filter(title="이력", parent__isnull=True).first()
    if not parent:
        return

    if MenuItem.objects.filter(title="늘봄허브등록", parent=parent).exists():
        return

    last = MenuItem.objects.filter(parent=parent).order_by("-order").first()
    order = (last.order + 1) if last else 40

    MenuItem.objects.create(
        title="늘봄허브등록",
        parent=parent,
        url="/teachers/nuribom-hub/",
        order=order,
        access_level="teacher",
    )


def remove_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(title="늘봄허브등록", url="/teachers/nuribom-hub/").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_add_certificate_catalog_menu"),
    ]

    operations = [
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
