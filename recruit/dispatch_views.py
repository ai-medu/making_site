"""출강 강사 모집 공고 - 목록은 로그인한 강사·관리자, 등록/수정/삭제는 관리자"""
import json
import re

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import DispatchRecruit

TEXT_FIELDS = ["title", "place", "place_address", "target", "subject", "content", "materials", "notes", "status"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@login_required
def dispatch_list(request):
    return render(request, "recruit/dispatch_list.html", {"recruits": DispatchRecruit.objects.all()})


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
    if not obj.title:
        obj.title = DispatchRecruit._meta.get_field("title").default

    programs = [p for p in request.POST.getlist("programs") if p in DispatchRecruit.PROGRAM_CHOICES]
    for p in (request.POST.get("program_custom") or "").split(","):
        p = p.strip()
        if p and p not in programs:
            programs.append(p)
    obj.programs = programs

    obj.pay_main = _amount(request.POST.get("pay_main"), 50000)
    obj.pay_assist = _amount(request.POST.get("pay_assist"), 30000)

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
