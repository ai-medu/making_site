from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.utils import send_kakao_message
from teachers.models import TeachingInstitution


class Command(BaseCommand):
    help = "견적발행일이 된(또는 지난) 출강장소를 강사에게 카카오톡 '나에게 보내기'로 알린다. 하루 한 번 cron 으로 실행."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        targets = []
        qs = TeachingInstitution.objects.filter(is_closed=False, quote_day__isnull=False).select_related('teacher', 'school')
        for inst in qs:
            if inst.quote_notified_on == today:
                continue
            if inst.quote_status(today) in ('due', 'overdue'):
                targets.append(inst)

        sent = 0
        for inst in targets:      # 학교마다 따로 보내서 '바로가기'가 그 학교·그 월 견적서 미리보기로 열리게 한다
            name = inst.school.name if inst.school else inst.name
            text = (f"[견적서 발행 알림]\n{name} {inst.quote_target_month()}월분 견적서를 발행할 차례입니다. (매월 {inst.quote_day}일)\n"
                    f"바로가기로 견적서를 확인·발송한 뒤 '출강장소'에서 발행완료를 눌러주세요.")
            res = send_kakao_message(inst.teacher, text, link_url=f"{settings.SITE_URL}{inst.quote_preview_path(today)}")
            if res.get("result_code") == 0:
                sent += 1
                TeachingInstitution.objects.filter(pk=inst.pk).update(quote_notified_on=today)
            else:
                self.stdout.write(f"{inst.teacher.username} {name}: 카카오 발송 실패 {res}")
        self.stdout.write(f"대상 {len(targets)}곳, 카카오 발송 {sent}곳")
