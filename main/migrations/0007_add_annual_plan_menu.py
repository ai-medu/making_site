from django.db import migrations


def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")

    parent = MenuItem.objects.filter(title="수업자료", parent__isnull=True).first()
    if not parent:
        return
    if MenuItem.objects.filter(title="연간계획서", parent=parent).exists():
        return

    last = MenuItem.objects.filter(parent=parent).order_by("-order").first()
    MenuItem.objects.create(
        title="연간계획서",
        parent=parent,
        url="/resources/plans/",
        order=(last.order + 1) if last else 1,
        access_level="teacher",
    )


def remove_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(title="연간계획서", url="/resources/plans/").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_aiapikey_and_menu"),
    ]

    operations = [
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
