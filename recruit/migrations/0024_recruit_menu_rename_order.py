from django.db import migrations

# (url, 새 제목, 아이콘, 순서) - 모집 메뉴: 지도사교육과정 → 출강강사모집 → 모집공고-광주 → 모집공고-전남
ITEMS = [
    ("/recruit/instructor/", "지도사교육과정", "bi-mortarboard", 11),
    ("/recruit/dispatch/", None, None, 12),
    ("/linkhub/?area=gwangju", "모집공고-광주", "bi-geo-alt", 13),
    ("/linkhub/?area=jeonnam", "모집공고-전남", "bi-pin-map", 14),
]


def forward(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    for url, title, icon, order in ITEMS:
        for m in MenuItem.objects.filter(url=url, parent__title="모집"):
            m.order = order
            if title:
                m.title = title
            if icon:
                m.icon_class = icon
            m.save()


class Migration(migrations.Migration):
    dependencies = [("recruit", "0023_dispatch_schedule_fields")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
