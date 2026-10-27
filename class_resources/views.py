from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

# ✅ 관리자 또는 강사만 접근 허용
def is_staff_or_teacher(user):
    # 프로필이 없는 경우(예: 관리자 계정)를 고려하여 getattr 사용
    profile = getattr(user, 'profile', None)
    user_type = getattr(profile, 'user_type', '') if profile else ''
    return user.is_staff or user_type in ('teacher', 'center_teacher')

@login_required
@user_passes_test(is_staff_or_teacher)
def resource_list(request):
    """전체 수업자료 메인 페이지"""
    categories = [
        {"slug": "3dpen", "name": "3D펜"},
        {"slug": "robot", "name": "로봇"},
        {"slug": "science", "name": "과학"},
        {"slug": "math", "name": "창의수학"},
        {"slug": "coding", "name": "코딩"},
        {"slug": "drone", "name": "항공드론"},
        {"slug": "career", "name": "진로체험"},
    ]
    return render(request, "class_resources/resource_list.html", {"categories": categories})


@login_required
@user_passes_test(is_staff_or_teacher)
def resource_detail(request, category):
    """각 과목별 상세자료 페이지"""
    template_name = f"class_resources/detail_{category}.html"
    return render(request, template_name, {"category": category})

# ✅ 로봇 세부 페이지
@login_required
@user_passes_test(is_staff_or_teacher)
def robot_olloai(request):
    return render(request, "class_resources/robot/olloai.html")

@login_required
@user_passes_test(is_staff_or_teacher)
def robot_probo(request):
    return render(request, "class_resources/robot/probo.html")

@login_required
@user_passes_test(is_staff_or_teacher)
def robot_xrobo(request):
    return render(request, "class_resources/robot/xrobo.html")

@login_required
@user_passes_test(is_staff_or_teacher)
def robot_jrobo(request):
    return render(request, "class_resources/robot/jrobo.html")

# ---------------------------------------------------------------------------
# 연간계획서 (PDF)
# ---------------------------------------------------------------------------
from django import forms
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import AnnualPlan

PLAN_MAX_BYTES = 11 * 1024 * 1024   # 서버(nginx) 업로드 제한 12MB 안쪽


class AnnualPlanForm(forms.ModelForm):
    class Meta:
        model = AnnualPlan
        fields = ["title", "category", "description", "pdf", "order"]

    def clean_pdf(self):
        f = self.cleaned_data["pdf"]
        if hasattr(f, "size") and not hasattr(f, "instance"):
            if not f.name.lower().endswith(".pdf"):
                raise forms.ValidationError("PDF 파일만 올릴 수 있습니다.")
            if f.size > PLAN_MAX_BYTES:
                raise forms.ValidationError("파일이 너무 큽니다. (최대 11MB)")
            head = f.read(5)
            f.seek(0)
            if head != b"%PDF-":
                raise forms.ValidationError("올바른 PDF 파일이 아닙니다.")
        return f


@login_required
@user_passes_test(is_staff_or_teacher)
def plan_list(request):
    cat = request.GET.get("cat", "")
    plans = AnnualPlan.objects.all()
    if cat in dict(AnnualPlan.CATEGORIES):
        plans = plans.filter(category=cat)
    else:
        cat = ""
    return render(request, "class_resources/plan_list.html", {
        "plans": plans, "cat": cat, "categories": AnnualPlan.CATEGORIES,
    })


@login_required
@user_passes_test(is_staff_or_teacher)
def plan_detail(request, pk):
    return render(request, "class_resources/plan_detail.html", {"plan": get_object_or_404(AnnualPlan, pk=pk)})


@login_required
@user_passes_test(is_staff_or_teacher)
def plan_file(request, pk):
    """PDF 보기(미리보기) / 다운로드(?download=1)"""
    plan = get_object_or_404(AnnualPlan, pk=pk)
    if not plan.pdf:
        raise Http404
    resp = FileResponse(plan.pdf.open("rb"), as_attachment=request.GET.get("download") == "1",
                        filename=f"{plan.title}.pdf", content_type="application/pdf")
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Cache-Control"] = "private, no-store"
    return resp


@login_required
@user_passes_test(lambda u: u.is_staff)
def plan_create(request):
    form = AnnualPlanForm(request.POST or None, request.FILES or None, initial={"category": request.GET.get("cat", "robot")})
    if request.method == "POST" and form.is_valid():
        plan = form.save()
        messages.success(request, f"'{plan.title}' 연간계획서를 등록했습니다.")
        return redirect("plan_list")
    return render(request, "class_resources/plan_form.html", {"form": form})


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(AnnualPlan, pk=pk)
    title = plan.title
    plan.delete()
    messages.success(request, f"'{title}' 연간계획서를 삭제했습니다.")
    return redirect("plan_list")
