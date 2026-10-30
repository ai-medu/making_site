"""출강 강사 모집 공고 - 목록은 로그인한 강사·관리자, 등록/수정/삭제는 관리자"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import DispatchRecruit

FIELDS = ["title", "schedule", "place", "time_info", "target", "subject", "content",
          "materials", "pay_main", "pay_assist", "notes", "status"]


@login_required
def dispatch_list(request):
    return render(request, "recruit/dispatch_list.html", {"recruits": DispatchRecruit.objects.all()})


def _save(request, obj):
    for f in FIELDS:
        setattr(obj, f, (request.POST.get(f) or "").strip())
    if obj.status not in dict(DispatchRecruit.STATUS_CHOICES):
        obj.status = "open"
    if not obj.title:
        obj.title = DispatchRecruit._meta.get_field("title").default
    obj.save()


@staff_member_required
def dispatch_add(request):
    if request.method == "POST":
        _save(request, DispatchRecruit())
        return redirect("dispatch_list")
    return render(request, "recruit/dispatch_form.html", {"obj": None})


@staff_member_required
def dispatch_edit(request, pk):
    obj = get_object_or_404(DispatchRecruit, pk=pk)
    if request.method == "POST":
        _save(request, obj)
        return redirect("dispatch_list")
    return render(request, "recruit/dispatch_form.html", {"obj": obj})


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
