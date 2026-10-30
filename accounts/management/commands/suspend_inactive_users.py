from django.core.management.base import BaseCommand

from accounts import suspension


class Command(BaseCommand):
    help = "최근 3개월 접속·교구 출고 내역이 없는 회원 계정을 정지합니다 (매일 1회 실행)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="정지하지 않고 대상만 보여줍니다.")

    def handle(self, *args, **opts):
        users = suspension.run(dry_run=opts["dry_run"])
        for u in users:
            self.stdout.write(f"{u.username} ({u.first_name}) 마지막 접속: {u.last_login or '없음'}")
        self.stdout.write(f"{'대상' if opts['dry_run'] else '정지'} {len(users)}명")
