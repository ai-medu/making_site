from django.db import migrations

# (URL, 아이콘, 순서) - 이력 메뉴: 출강장소 → 학력관리 → 경력관리 → 자격증관리 → 자격증리스트 → 늘봄허브등록
HISTORY = [
    ("/teachers/institutions/", None, 1),
    ("/teachers/educations/", "bi-mortarboard", 2),
    ("/teachers/careers/", None, 3),
    ("/teachers/certificates/", None, 4),
    ("/teachers/certificate-catalog/", "bi-list-check", 5),
    ("/teachers/nuribom-hub/", "bi-file-earmark-text", 6),
]


def apply(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")

    parent = MenuItem.objects.filter(title="이력", parent__isnull=True).first()
    if parent:
        base = min(parent.sub_menus.values_list("order", flat=True) or [34])
        for url, icon, pos in HISTORY:
            for item in MenuItem.objects.filter(parent=parent, url=url):
                item.order = base + pos - 1
                if icon and not item.icon_class:
                    item.icon_class = icon
                item.save()

    study = MenuItem.objects.filter(title="수업자료", parent__isnull=True).first()
    if study:
        plan = MenuItem.objects.filter(parent=study, url="/resources/plans/").first()
        if plan:
            others = study.sub_menus.exclude(pk=plan.pk).values_list("order", flat=True)
            plan.order = (min(others) - 1) if others else 1     # 맨 위로
            plan.icon_class = plan.icon_class or "bi-calendar3-range"
            plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_add_annual_plan_menu"),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
