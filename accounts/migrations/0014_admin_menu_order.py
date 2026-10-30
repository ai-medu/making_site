from django.db import migrations

# (url, 새 제목 또는 None, 아이콘 또는 None, 순서) - 관리 메뉴 정리: 공지사항 → 회원목록 → 회원승인 → 회원정지 → 미디어 → 메뉴관리 → API관리
ITEMS = [
    ("/notices/", None, None, 7),
    ("/accounts/members/", None, None, 8),
    ("/accounts/approve_users/", None, None, 9),
    ("/accounts/suspended_users/", None, "bi-person-x", 10),
    ("/admin/filebrowser/browse/", None, None, 11),
    ("/menu-management/", None, None, 12),
    ("/ai-manage/", "API관리", "bi-key", 13),
]


def forward(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    for url, title, icon, order in ITEMS:
        for m in MenuItem.objects.filter(url=url, parent__title="관리"):
            m.order = order
            if title:
                m.title = title
            if icon:
                m.icon_class = icon
            m.save()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_menu_suspended_users")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
