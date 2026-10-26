from django.db import migrations

# '직책'이던 항목이 '프로그램명'으로 바뀜에 따라, 정확히 일치하는 값만 프로그램명으로 정리
# (다른 값은 건드리지 않음: 방과후 강사, 진로강사 등은 각자 수정)
RENAMES = {
    "로봇과학부 강사": "로봇과학",
    "로봇과학 강사": "로봇과학",
}


def normalize(apps, schema_editor):
    Career = apps.get_model("teachers", "Career")
    for old, new in RENAMES.items():
        Career.objects.filter(position=old).update(position=new)


class Migration(migrations.Migration):

    dependencies = [
        ("teachers", "0022_career_program_label"),
    ]

    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
    ]
