from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.utils import send_kakao_message
from teachers.models import TeachingInstitution


class Command(BaseCommand):
    help = "견적발행일이 된(또는 지난) 출강장소를 강사에게 카카오톡 '나에게 보내기'로 알린다. 하루 한 번 cron 으로 실행."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        by_teacher = defaultdict(list)
        qs = TeachingInstitution.objects.filter(is_closed=False, quote_day__isnull=False).select_related('teacher', 'school')
        for inst in qs:
            if inst.quote_notified_on == today:
                continue
            if inst.quote_status(today) in ('due', 'overdue'):
                by_teacher[inst.teacher].append(inst)

        sent = 0
        for teacher, insts in by_teacher.items():
            names = "\n".join(f"- {i.school.name if i.school else i.name} ({i.quote_target_month()}월분, 매월 {i.quote_day}일)" for i in insts)
            text = f"[견적서 발행 알림]\n견적서를 발행할 출강장소가 있습니다.\n{names}\n발행 후 '출강장소'에서 발행완료를 눌러주세요."
            res = send_kakao_message(teacher, text, link_url=f"{settings.SITE_URL}/teachers/institutions/")
            if res.get("result_code") == 0:
                sent += 1
                TeachingInstitution.objects.filter(pk__in=[i.pk for i in insts]).update(quote_notified_on=today)
            else:
                self.stdout.write(f"{teacher.username}: 카카오 발송 실패 {res}")
        self.stdout.write(f"대상 강사 {len(by_teacher)}명, 카카오 발송 {sent}명")
