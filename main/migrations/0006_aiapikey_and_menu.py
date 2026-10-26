from django.db import migrations, models


def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")

    parent = MenuItem.objects.filter(title="관리", parent__isnull=True).first()
    if not parent:
        return
    if MenuItem.objects.filter(title="AI관리", parent=parent).exists():
        return

    last = MenuItem.objects.filter(parent=parent).order_by("-order").first()
    MenuItem.objects.create(
        title="AI관리",
        parent=parent,
        url="/ai-manage/",
        order=(last.order + 1) if last else 50,
        access_level="staff",
    )


def remove_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("main", "MenuItem")
    MenuItem.objects.filter(title="AI관리", url="/ai-manage/").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_add_education_menu"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIApiKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(help_text="구분하기 위한 이름 (예: 메인 키, 예비 키)", max_length=100, verbose_name="이름")),
                ("provider", models.CharField(choices=[("gemini", "Google Gemini")], default="gemini", max_length=20, verbose_name="서비스")),
                ("api_key", models.CharField(max_length=255, verbose_name="API 키")),
                ("is_active", models.BooleanField(default=True, verbose_name="사용")),
                ("order", models.PositiveIntegerField(default=0, help_text="작은 숫자부터 먼저 사용합니다. 사용량이 초과되면 다음 키를 사용합니다.", verbose_name="사용 순서")),
                ("memo", models.CharField(blank=True, max_length=200, verbose_name="메모")),
                ("success_count", models.PositiveIntegerField(default=0, verbose_name="성공 횟수")),
                ("fail_count", models.PositiveIntegerField(default=0, verbose_name="실패 횟수")),
                ("last_used_at", models.DateTimeField(blank=True, null=True, verbose_name="마지막 사용")),
                ("last_error", models.CharField(blank=True, max_length=300, verbose_name="마지막 오류")),
                ("last_error_at", models.DateTimeField(blank=True, null=True, verbose_name="마지막 오류 시각")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "AI API 키",
                "verbose_name_plural": "AI API 키",
                "ordering": ["order", "id"],
            },
        ),
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
