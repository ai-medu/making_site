"""장기 미접속·미거래 회원 계정 정지

정지 기준: 최근 3개월 동안 접속(로그인)한 적이 없고, 최근 3개월 동안 교구 출고 내역도 없는 회원.
- 가입한 지 3개월이 안 된 회원, 관리자(staff), 승인 대기(is_active=False) 회원은 대상이 아님
- 정지하면 User.is_active=False 로 바꿔 로그인을 막고, Profile.suspended_at 에 시각을 남김
  (승인 대기 회원과 구분하기 위해 suspended_at 이 있으면 '정지', 없으면 '승인 대기')
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from .models import Profile

INACTIVE_DAYS = 90
REASON = "최근 3개월 접속·교구 출고 내역 없음"


def candidates(now=None):
    from materials.models import MaterialRelease
    now = now or timezone.now()
    cutoff = now - timedelta(days=INACTIVE_DAYS)
    recent_teachers = MaterialRelease.objects.filter(created_at__gte=cutoff).values("teacher_id")
    return (
        User.objects.filter(is_active=True, is_staff=False, is_superuser=False, date_joined__lt=cutoff)
        .filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
        .exclude(id__in=recent_teachers)
        .exclude(profile__withdrawal_requested=True)
    )


def suspend(user, reason=REASON, now=None):
    now = now or timezone.now()
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"phone_number": ""})
    profile.suspended_at = now
    profile.suspend_reason = reason
    profile.save(update_fields=["suspended_at", "suspend_reason"])
    user.is_active = False
    user.save(update_fields=["is_active"])


def restore(user):
    """정지 해제 - 다시 로그인할 수 있게 하고, 3개월 기준이 바로 다시 적용되지 않도록 접속 기준일을 지금으로 맞춤"""
    now = timezone.now()
    Profile.objects.filter(user=user).update(suspended_at=None, suspend_reason="")
    user.is_active = True
    user.last_login = now
    user.save(update_fields=["is_active", "last_login"])


def run(dry_run=False):
    qs = list(candidates())
    if not dry_run:
        for u in qs:
            suspend(u)
    return qs
