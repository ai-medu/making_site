"""출강 강사 모집 공고 - 목록·지원은 로그인한 사용자, 등록/수정/삭제/지원자 관리는 관리자"""
import json
import re
from datetime import date

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DispatchApplication, DispatchRecruit

TEXT_FIELDS = ["title", "place", "place_address", "target", "subject", "content", "materials", "notes", "status"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _ordered():
    """모집중 공고를 먼저, 그 안에서는 최신 등록순 (마감은 아래로)"""
    return sorted(DispatchRecruit.objects.all(), key=lambda r: (r.status != "open", -r.created_at.timestamp()))


@login_required
def dispatch_list(request):
    DispatchRecruit.close_expired()           # 마감일이 지난 공고는 자동 마감
    recruits = _ordered()
    mine = {a.recruit_id: a for a in DispatchApplication.objects.filter(user=request.user)}
    for r in recruits:
        r.my_application = mine.get(r.id)
    pending = DispatchApplication.objects.filter(status="pending").count() if request.user.is_staff else 0
    return render(request, "recruit/dispatch_list.html", {
        "recruits": recruits, "pending_count": pending,
        "role_choices": DispatchApplication.ROLE_CHOICES,
    })


def _schedule(raw):
    """폼에서 온 일정·시간 JSON 을 검증해 정리"""
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return None
    items = []
    for it in data.get("items", []):
        d, s, e = it.get("date", ""), it.get("start", ""), it.get("end", "")
        if DATE_RE.match(d) and TIME_RE.match(s) and TIME_RE.match(e):
            items.append({"date": d, "start": s, "end": e})
    items.sort(key=lambda x: x["date"])
    return {"same": bool(data.get("same", True)), "items": items} if items else None


def _amount(raw, default):
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return default


def _save(request, obj):
    for f in TEXT_FIELDS:
        setattr(obj, f, (request.POST.get(f) or "").strip())
    if obj.status not in dict(DispatchRecruit.STATUS_CHOICES):
        obj.status = "open"
    if not obj.title:      # 제목을 비워두면 '장소 주제 강사 모집'으로 자동 생성
        obj.title = DispatchRecruit.auto_title(obj.place, obj.subject)

    programs = [p for p in request.POST.getlist("programs") if p in DispatchRecruit.PROGRAM_CHOICES]
    for p in (request.POST.get("program_custom") or "").split(","):
        p = p.strip()
        if p and p not in programs:
            programs.append(p)
    obj.programs = programs

    obj.pay_main = _amount(request.POST.get("pay_main"), 50000)
    obj.pay_assist = _amount(request.POST.get("pay_assist"), 30000)

    raw_deadline = (request.POST.get("deadline") or "").strip()
    try:
        obj.deadline = date.fromisoformat(raw_deadline) if raw_deadline else None
    except ValueError:
        obj.deadline = None
    # 이미 지난 마감일이면 저장과 함께 마감 처리, 마감일을 미래로 고치면 다시 모집중으로 (수동 마감은 유지)
    if obj.deadline and obj.deadline < timezone.localdate() and obj.status == "open":
        obj.status = "closed"

    sched = _schedule(request.POST.get("schedule_json"))
    if sched:
        obj.schedule_data = sched
        obj.build_display()
    obj.save()


def _form_context(obj):
    programs = (obj.programs if obj else []) or []
    return {
        "obj": obj,
        "program_choices": DispatchRecruit.PROGRAM_CHOICES,
        "selected_programs": [p for p in programs if p in DispatchRecruit.PROGRAM_CHOICES],
        "custom_programs": ", ".join(p for p in programs if p not in DispatchRecruit.PROGRAM_CHOICES),
    }


@staff_member_required
def dispatch_add(request):
    if request.method == "POST":
        _save(request, DispatchRecruit())
        return redirect("dispatch_list")
    return render(request, "recruit/dispatch_form.html", _form_context(None))


@staff_member_required
def dispatch_edit(request, pk):
    obj = get_object_or_404(DispatchRecruit, pk=pk)
    if request.method == "POST":
        _save(request, obj)
        return redirect("dispatch_list")
    return render(request, "recruit/dispatch_form.html", _form_context(obj))


@staff_member_required
@require_POST
def dispatch_delete(request, pk):
    get_object_or_404(DispatchRecruit, pk=pk).delete()
    return redirect("dispatch_list")


@staff_member_required
@require_POST
def dispatch_toggle(request, pk):
    obj = get_object_or_404(DispatchRecruit, pk=pk)
    obj.status = "closed" if obj.status == "open" else "open"
    obj.save(update_fields=["status"])
    return redirect("dispatch_list")


# ---------------- 지원 ----------------
@login_required
@require_POST
def dispatch_apply(request, pk):
    DispatchRecruit.close_expired()
    recruit = get_object_or_404(DispatchRecruit, pk=pk)
    if recruit.status != "open":
        messages.error(request, "모집이 마감된 공고입니다.")
        return redirect("dispatch_list")
    role = request.POST.get("role")
    if role not in dict(DispatchApplication.ROLE_CHOICES):
        role = "any"
    app, created = DispatchApplication.objects.get_or_create(
        recruit=recruit, user=request.user,
        defaults={"role": role, "memo": (request.POST.get("memo") or "").strip()[:300]})
    if created:
        messages.success(request, "강사 지원이 접수되었습니다. 승인 결과는 이 화면에서 확인할 수 있습니다.")
    else:
        messages.info(request, "이미 지원한 공고입니다.")
    return redirect("dispatch_list")


@login_required
@require_POST
def dispatch_apply_cancel(request, pk):
    """본인 지원 취소 (대기 중일 때만)"""
    app = get_object_or_404(DispatchApplication, recruit_id=pk, user=request.user)
    if app.status == "pending":
        app.delete()
        messages.success(request, "지원을 취소했습니다.")
    else:
        messages.error(request, "이미 처리된 지원은 취소할 수 없습니다. 관리자에게 문의해주세요.")
    return redirect("dispatch_list")


# ---------------- 지원강사 관리 (관리자) ----------------
@staff_member_required
def dispatch_applications(request):
    DispatchRecruit.close_expired()
    recruits = _ordered()
    apps = DispatchApplication.objects.select_related("user", "user__profile", "recruit")
    by_recruit = {}
    for a in apps:
        by_recruit.setdefault(a.recruit_id, []).append(a)
    for r in recruits:
        r.apps = by_recruit.get(r.id, [])
        r.pending_n = sum(1 for a in r.apps if a.status == "pending")
        r.approved_n = sum(1 for a in r.apps if a.status == "approved")
    only = request.GET.get("recruit")
    if only and only.isdigit():
        recruits = [r for r in recruits if r.id == int(only)]
    return render(request, "recruit/dispatch_applications.html", {"recruits": recruits, "only": only})


@staff_member_required
@require_POST
def dispatch_application_action(request, pk):
    app = get_object_or_404(DispatchApplication, pk=pk)
    action = request.POST.get("action")
    name = app.user.first_name or app.user.username
    if action in ("approved", "rejected", "pending"):
        app.status = action
        app.save(update_fields=["status"])
        messages.success(request, f"{name} 강사: {app.get_status_display()} 처리했습니다.")
    elif action == "delete":
        app.delete()
        messages.success(request, f"{name} 강사의 지원 내역을 삭제했습니다.")
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/recruit/dispatch/") else "dispatch_applications")
