import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from teachers.models import TeachingInstitution
from .models import ProgramDivision, Student, MedutechAccount, MedutechSchoolMapping
from . import medutech_client
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation


from django.http import HttpResponseForbidden
from .forms import StudentForm
from django.contrib import messages
from django.db.models import Count, Q, Prefetch


def _get_accessible_institutions(user):
    if user.is_staff:
        return TeachingInstitution.objects.all()
    return TeachingInstitution.objects.filter(teacher=user)


@login_required
def student_list(request):
    """출강장소별 학생 목록 보기"""
    institutions = _get_accessible_institutions(request.user).prefetch_related('divisions__students')

    return render(request, 'students/student_list.html', {
        'institutions': institutions
    })

from django.db.models import Count, Prefetch, IntegerField
from django.db.models.functions import Cast

@login_required
def student_detail(request, institution_id):
    institution = get_object_or_404(TeachingInstitution, id=institution_id)

    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    divisions = (
        ProgramDivision.objects
        .filter(institution=institution)
        .annotate(student_count=Count('students'))
        .order_by('division')
        .prefetch_related(
            Prefetch(
                'students',
                queryset=Student.objects.annotate(
                    grade_int=Cast('grade', IntegerField()),
                    class_int=Cast('class_name', IntegerField()),
                    number_int=Cast('number', IntegerField()),
                ).order_by(
                    'grade_int',
                    'class_int',
                    'number_int',
                )
            )
        )
    )


    division_summary = []
    total_students = 0
    for div in divisions:
        if div.division and "미수강" not in div.division and div.student_count > 0:
            division_summary.append(f"{div.division} {div.student_count}명")
            total_students += div.student_count

    return render(request, 'students/student_detail.html', {
        'institution': institution,
        'institutions': _get_accessible_institutions(request.user),
        'divisions': divisions,
        'division_summary': " / ".join(division_summary) if division_summary else "등록된 학생 없음",
        'total_students': total_students,
        'medutech_mapping': MedutechSchoolMapping.objects.filter(institution=institution).first(),
    })



@login_required
def student_upload(request):
    """엑셀 업로드로 학생 일괄 등록"""
    if request.user.is_staff:
        institutions = TeachingInstitution.objects.all()
    else:
        institutions = TeachingInstitution.objects.filter(teacher=request.user)

    if request.method == 'POST':
        selected_id = request.POST.get('institution_id')
        excel_file = request.FILES.get('excel_file')

        if not selected_id or not excel_file:
            return render(request, 'students/student_upload.html', {
                'institutions': institutions,
                'error': "출강장소와 엑셀 파일을 모두 선택해주세요."
            })

        institution = get_object_or_404(TeachingInstitution, id=selected_id)
        df = pd.read_excel(excel_file, dtype=str)  # ✅ 모든 칸 문자열로 읽기 (NaN 방지)
        df = df.replace({pd.NA: None, 'nan': None, 'NaN': None})  # ✅ NaN/빈칸 정리
        df = df.dropna(subset=['학생이름'])  # ✅ 학생이름이 비어있으면 행 제거

        required_cols = ['부서', '학년', '반', '번호', '학생이름', '학부모연락처']
        if not all(col in df.columns for col in required_cols):
            return render(request, 'students/student_upload.html', {
                'institutions': institutions,
                'error': f"엑셀에 다음 항목이 모두 포함되어야 합니다: {', '.join(required_cols)}"
            })

        # ✅ 데이터 저장
        for _, row in df.iterrows():
            division_name = str(row['부서']).strip()
            if not division_name:
                continue

            division, _ = ProgramDivision.objects.get_or_create(
                institution=institution, division=division_name
            )

            # 숫자형 컬럼 정리: 문자열에서 숫자만 추출
            def to_int_str(val):
                try:
                    return str(int(float(val))) if val not in [None, ''] else ''
                except:
                    return str(val).strip()

            grade = to_int_str(row['학년'])
            class_name = to_int_str(row['반'])
            number = to_int_str(row['번호'])

            Student.objects.create(
                division=division,
                grade=grade,
                class_name=class_name,
                number=number,
                name=str(row['학생이름']).strip(),
                parent_contact=str(row['학부모연락처']).strip() if row['학부모연락처'] else '',
            )

        return redirect('students:student_detail', institution_id=institution.id)

    return render(request, 'students/student_upload.html', {'institutions': institutions})


@login_required
def student_template(request):
    """엑셀 양식 다운로드 (부서 드롭다운 포함, 예시 데이터 제거)"""
    wb = Workbook()
    ws = wb.active
    ws.title = "학생등록양식"

    headers = ['부서', '학년', '반', '번호', '학생이름', '학부모연락처']
    ws.append(headers)

    # ✅ 드롭다운 설정
    dv = DataValidation(
        type="list",
        formula1='"1부,2부,3부,미수강"',
        allow_blank=False,
        showDropDown=False,
        promptTitle="부서 선택",
        prompt="1부, 2부, 3부, 미수강 중에서 선택하세요.",
        showErrorMessage=True,
        errorTitle="잘못된 입력",
        error="부서는 반드시 지정된 목록 중 하나를 선택해야 합니다."
    )
    ws.add_data_validation(dv)
    for row in range(2, 201):
        dv.add(ws[f"A{row}"])

    # ✅ 서식만 살짝 추가 (보기 좋게)
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 8
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 18

    # ✅ 예시 데이터 삭제 (ws.append 제거)
    # (홍길동, 예시 데이터 전혀 없음)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="student_upload_template.xlsx"'
    wb.save(response)
    return response

@login_required
def student_create(request, institution_id):
    institution = get_object_or_404(TeachingInstitution, id=institution_id)

    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            # ✅ 부서명 문자열
            division_name = form.cleaned_data['division']

            # ✅ 출강장소 기준 ProgramDivision 확인/생성
            division, _ = ProgramDivision.objects.get_or_create(
                institution=institution,
                division=division_name,
                defaults={'capacity': 0}
            )

            # ✅ Student 객체 수동 생성
            Student.objects.create(
                division=division,
                grade=form.cleaned_data['grade'],
                class_name=form.cleaned_data['class_name'],
                number=form.cleaned_data['number'],
                name=form.cleaned_data['name'],
                parent_contact=form.cleaned_data['parent_contact'],
            )

            return redirect('students:student_detail', institution_id=institution.id)
    else:
        form = StudentForm()

    return render(request, 'students/student_form.html', {
        'form': form,
        'institution': institution,
        'title': '학생 추가',
    })


@login_required
def student_update(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    institution = student.division.institution

    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            division_name = form.cleaned_data['division']
            division, _ = ProgramDivision.objects.get_or_create(
                institution=institution,
                division=division_name,
                defaults={'capacity': 0}
            )

            student.division = division
            student.grade = form.cleaned_data['grade']
            student.class_name = form.cleaned_data['class_name']
            student.number = form.cleaned_data['number']
            student.name = form.cleaned_data['name']
            student.parent_contact = form.cleaned_data['parent_contact']
            student.save()

            return redirect('students:student_detail', institution_id=institution.id)
    else:
        form = StudentForm(initial={
            'division': student.division.division,
            'grade': student.grade,
            'class_name': student.class_name,
            'number': student.number,
            'name': student.name,
            'parent_contact': student.parent_contact,
        })

    return render(request, 'students/student_form.html', {
        'form': form,
        'institution': institution,
        'title': '학생 수정',
    })

@login_required
def student_delete(request, student_id):
    """학생 삭제"""
    student = get_object_or_404(Student, id=student_id)
    institution = student.division.institution

    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    if request.method == 'POST':
        student.delete()
        return redirect('students:student_detail', institution_id=institution.id)

    return render(request, 'students/student_confirm_delete.html', {
        'student': student,
        'institution': institution,
    })

@login_required
def student_reset(request, institution_id):
    """출강장소별 학생 전체 삭제 (관리자 또는 해당 강사만 가능)"""
    institution = get_object_or_404(TeachingInstitution, id=institution_id)

    # 권한 확인
    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    if request.method == "POST":
        # ✅ 해당 출강장소의 모든 학생 삭제
        deleted_count = Student.objects.filter(division__institution=institution).delete()[0]
        messages.success(request, f"{deleted_count}명의 학생이 삭제되었습니다.")
        return redirect("students:student_detail", institution_id=institution.id)

    return render(request, "students/student_reset_confirm.html", {
        "institution": institution,
    })


from django.views.decorators.http import require_POST
from django.db import transaction

@require_POST
@login_required
def student_bulk_move(request):
    student_ids = request.POST.getlist("student_ids")
    target_division_name = request.POST.get("target_division")
    institution_id = request.POST.get("institution_id")

    if not student_ids or not target_division_name:
        messages.error(request, "이동할 학생과 부서를 선택해주세요.")
        return redirect("students:student_detail", institution_id=institution_id)

    institution = get_object_or_404(TeachingInstitution, id=institution_id)

    # 권한 체크
    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    # 대상 부서 가져오기 or 생성
    target_division, _ = ProgramDivision.objects.get_or_create(
        institution=institution,
        division=target_division_name
    )

    with transaction.atomic():
        Student.objects.filter(id__in=student_ids).update(
            division=target_division
        )

    messages.success(
        request,
        f"{len(student_ids)}명의 학생을 [{target_division_name}]로 이동했습니다."
    )

    return redirect("students:student_detail", institution_id=institution.id)


@login_required
def medutech_settings(request):
    """출첵마스터 API 토큰 등록/수정 (계정당 1회, 학교별 매핑은 자동 진행)"""
    account = MedutechAccount.objects.filter(user=request.user).first()

    if request.method == 'POST':
        token = request.POST.get('api_token', '').strip()
        if not token:
            messages.error(request, "API 토큰을 입력해주세요.")
        else:
            try:
                medutech_client.get_schools(token)
            except medutech_client.MedutechAPIError as exc:
                messages.error(request, str(exc))
            else:
                MedutechAccount.objects.update_or_create(
                    user=request.user, defaults={'api_token': token}
                )
                matched, total = medutech_client.auto_match_schools(request.user)
                messages.success(
                    request,
                    f"출첵마스터 연동이 완료되었습니다. (출강장소 {total}곳 중 {matched}곳 자동 연동)"
                )
                return redirect('students:medutech_settings')

    return render(request, 'students/medutech_settings.html', {'account': account})


@require_POST
@login_required
def medutech_rematch(request):
    """출강장소가 새로 추가된 경우 등, 이름 일치 매핑을 다시 시도"""
    account = MedutechAccount.objects.filter(user=request.user).first()
    if not account:
        messages.error(request, "먼저 출첵마스터 API 토큰을 등록해주세요.")
        return redirect('students:medutech_settings')

    try:
        matched, total = medutech_client.auto_match_schools(request.user)
    except medutech_client.MedutechAPIError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"자동 연동을 다시 시도했습니다. (신규 매칭 {matched}건)")

    return redirect('students:medutech_settings')


@login_required
def medutech_map_institution(request, institution_id):
    """출강장소 <-> medutech.kr 학교 매핑"""
    institution = get_object_or_404(TeachingInstitution, id=institution_id)
    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    account = MedutechAccount.objects.filter(user=request.user).first()
    if not account:
        messages.error(request, "먼저 출첵마스터 API 토큰을 등록해주세요.")
        return redirect('students:medutech_settings')

    mapping = MedutechSchoolMapping.objects.filter(institution=institution).first()

    try:
        schools = medutech_client.get_schools(account.api_token)
    except medutech_client.MedutechAPIError as exc:
        messages.error(request, str(exc))
        schools = []

    if request.method == 'POST':
        school_id = request.POST.get('medutech_school_id')
        selected = next((s for s in schools if str(s['id']) == school_id), None)
        if not selected:
            messages.error(request, "선택한 학교 정보를 확인할 수 없습니다.")
        else:
            MedutechSchoolMapping.objects.update_or_create(
                institution=institution,
                defaults={
                    'medutech_school_id': selected['id'],
                    'medutech_school_name': selected['name'],
                    'medutech_program_name': selected.get('program_name', ''),
                }
            )
            messages.success(request, f"'{selected['name']}'(으)로 연동되었습니다.")
            return redirect('students:student_detail', institution_id=institution.id)

    return render(request, 'students/medutech_map.html', {
        'institution': institution,
        'mapping': mapping,
        'schools': schools,
    })


@require_POST
@login_required
def medutech_sync_students(request, institution_id):
    """medutech.kr에서 학생 목록을 가져와 로컬 Student와 동기화"""
    institution = get_object_or_404(TeachingInstitution, id=institution_id)
    if not request.user.is_staff and institution.teacher != request.user:
        return HttpResponseForbidden("접근 권한이 없습니다.")

    account = MedutechAccount.objects.filter(user=request.user).first()
    mapping = MedutechSchoolMapping.objects.filter(institution=institution).first()

    if not account:
        messages.error(request, "먼저 출첵마스터 API 토큰을 등록해주세요.")
        return redirect('students:medutech_settings')
    if not mapping:
        messages.error(request, "이 출강장소와 이름이 일치하는 출첵마스터 학교를 찾지 못했습니다. 수동으로 연동해주세요.")
        return redirect('students:medutech_map_institution', institution_id=institution.id)

    try:
        items, synced_month = medutech_client.get_recent_students(account.api_token, mapping.medutech_school_id)
    except medutech_client.MedutechAPIError as exc:
        messages.error(request, str(exc))
        return redirect('students:student_detail', institution_id=institution.id)

    if not items:
        messages.warning(
            request,
            "출첵마스터에서 학생 목록을 받아오지 못했습니다(0명). 실수로 전체 삭제되는 것을 막기 위해 동기화를 건너뛰었습니다."
        )
        return redirect('students:student_detail', institution_id=institution.id)

    created_count = 0
    updated_count = 0
    seen_medutech_ids = set()

    with transaction.atomic():
        for item in items:
            medutech_student_id = item.get('id')
            seen_medutech_ids.add(medutech_student_id)

            division_name = (item.get('department') or '미수강').strip()
            division, _ = ProgramDivision.objects.get_or_create(
                institution=institution, division=division_name
            )

            field_values = {
                'division': division,
                'grade': str(item.get('grade') or ''),
                'class_name': str(item.get('classroom') or ''),
                'number': str(item.get('number') or ''),
                'name': item.get('name') or '',
                'parent_contact': item.get('phone') or '',
                'medutech_student_id': medutech_student_id,
            }

            student = Student.objects.filter(
                division__institution=institution,
                medutech_student_id=medutech_student_id,
            ).first()

            if student:
                for field, value in field_values.items():
                    setattr(student, field, value)
                student.save()
                updated_count += 1
            else:
                Student.objects.create(**field_values)
                created_count += 1

        # 출첵마스터 명단과 완전히 동일해지도록, 이제 없는 학생은 로컬에서도 제거
        # (예전에 수동/엑셀로 등록되어 medutech_student_id가 없는 중복 항목도 함께 정리됨)
        removed_count, _ = Student.objects.filter(
            division__institution=institution
        ).exclude(medutech_student_id__in=seen_medutech_ids).delete()

    month_label = f" ({synced_month} 기준)" if synced_month else ""
    messages.success(
        request,
        f"출첵마스터 동기화 완료{month_label}: 신규 {created_count}명, 갱신 {updated_count}명, 삭제 {removed_count}명."
    )
    return redirect('students:student_detail', institution_id=institution.id)



# ======================================================================
# 늘봄학교 평가 통지서
# ======================================================================
import json
import re
from datetime import date

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import EvaluationNotice


def _eval_institution(request, institution_id):
    inst = get_object_or_404(TeachingInstitution, id=institution_id)
    if not request.user.is_staff and inst.teacher != request.user:
        return None
    return inst


def _clean_eval_html(html):
    """저장·불러오기 때 스크립트·이벤트 속성 제거"""
    html = re.sub(r"(?is)<(script|iframe|object|embed|link|style|meta|form)\b.*?(</\1>|/>|>)", "", html or "")
    html = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html)
    html = re.sub(r"(?i)(href|src)\s*=\s*([\"']?)\s*javascript:", r"\1=\2#", html)
    return html


@login_required
def evaluation_list(request):
    """평가통지서를 작성할 출강장소(학교) 선택"""
    institutions = _get_accessible_institutions(request.user)
    return render(request, 'students/evaluation_list.html', {'institutions': institutions})


@login_required
def evaluation_page(request, institution_id):
    inst = _eval_institution(request, institution_id)
    if inst is None:
        return HttpResponseForbidden("접근 권한이 없습니다.")
    today = timezone.localdate()
    default_year = today.year if today.month >= 3 else today.year - 1
    default_sem = 1 if 3 <= today.month <= 8 else 2
    student_groups = _eval_student_rows(inst)
    return render(request, 'students/evaluation_page.html', {
        'institution': inst,
        'default_year': default_year,
        'default_sem': default_sem,
        'months': list(range(1, 13)),
        'default_start': 3 if default_sem == 1 else 9,
        'default_end': 7 if default_sem == 1 else 12,
        'student_groups': student_groups,
        'guide_options': _guide_options(inst.program),
        'student_total': sum(len(g['rows']) for g in student_groups),
        'saved': EvaluationNotice.objects.filter(institution=inst),
        'load_id': request.GET.get('load', ''),
    })


_ROBOT_PREFIX = (("엑스로보", "xrobo"), ("올로AI", "olloai"), ("제이로보", "jrobo"), ("커넥트", "connect"), ("테크닉", "technic"), ("큐보", "cubo"))


def _guide_key(material_name):
    """교구명(예: '올로AI Lv4', '엑스로보 Lv4-2(SD)') → (로봇, 단계) 키. 안내 문구가 없는 교구면 None"""
    name = (material_name or "").strip()
    robot = next((key for prefix, key in _ROBOT_PREFIX if name.startswith(prefix)), None)
    m = re.search(r"Lv\s*([0-9.]+)(?:-\d+)?\s*(?:\(([^)]+)\))?", name, re.I)
    if not robot or not m:
        return None
    stage = (m.group(2) or m.group(1)).strip()
    return robot, f"{stage}단계"


def _current_guides(inst, students):
    """학생별 '현재 단계': 단계업 기록 중 안내 문구가 있는 교구의 가장 최근(년월 → 등록순) 기록.
    반환: {학생id: {"title": "커넥트 1단계", "text": 안내 문구}} (해당 없으면 키 없음)"""
    from robot_LvUP.models import RobotLevelUp, LevelUpGuide
    guides = {(g.robot, g.stage): (g.id, g.text) for g in LevelUpGuide.objects.all()}
    records = RobotLevelUp.objects.filter(institution=inst).select_related("material").order_by("year_month", "id")
    latest, by_key = {}, {}
    for r in records:                       # 나중 기록이 앞 기록을 덮어씀 (공구함처럼 안내 문구가 없는 교구는 건너뜀)
        key = _guide_key(r.material.name) if r.material_id else None
        if not key or key not in guides:
            continue
        label = next((p for p, k in _ROBOT_PREFIX if k == key[0]), key[0])
        info = {"id": guides[key][0], "title": f"{label} {key[1]}", "text": guides[key][1]}
        if r.student_id:
            latest[r.student_id] = info
        by_key[(str(r.grade or ""), str(r.class_no or ""), str(r.student_no or ""), (r.student_name or "").strip())] = info
    out = {}
    for st in students:
        info = latest.get(st.id) or by_key.get((str(st.grade), str(st.class_name), str(st.number), st.name.strip()))
        if info:
            out[st.id] = info
    return out


def _guide_info(guide):
    """LevelUpGuide → 학습내용 칸에 넣을 {"title", "text"}"""
    label = next((p for p, k in _ROBOT_PREFIX if k == guide.robot), guide.get_robot_display())
    return {"id": guide.id, "title": f"{label} {guide.stage}", "text": guide.text}


_PROGRAM_HINTS = (("로봇", ("xrobo", "olloai", "jrobo", "connect", "technic", "cubo")), ("과학", ("science",)), ("수학", ("math",)),
                  ("3d", ("pen3d",)), ("펜", ("pen3d",)), ("코딩", ("coding",)), ("드론", ("drone",)))


def _guide_options(program=""):
    """단계 선택 목록: [(분류 이름, [(안내 id, 단계)])] - 학교의 프로그램과 맞는 분류를 앞에 둠"""
    from robot_LvUP.models import LevelUpGuide
    prog = (program or "").lower()
    first = {k for hint, keys in _PROGRAM_HINTS if hint in prog for k in keys}
    out = []
    for key, label in LevelUpGuide.ROBOTS:
        items = [(g.id, g.stage) for g in LevelUpGuide.objects.filter(robot=key).order_by('order', 'id')]
        if items:
            out.append((0 if key in first else 1, label, items))
    out.sort(key=lambda x: x[0])           # 안정 정렬: 맞는 분류가 먼저, 나머지는 원래 순서
    return [(label, items) for _, label, items in out]


def _school_year_of(year, month):
    """학년도(3월~다음해 2월) 기준 달력 연도: 3~12월은 학년도 연도, 1~2월은 다음 해"""
    return year if month >= 3 else year + 1


def _eval_students(inst):
    """평가통지서 대상: 현재 1부·2부·3부 학생만 ('미수강' 부서 학생은 제외)"""
    return list(
        Student.objects.filter(division__institution=inst, division__division__in=['1부', '2부', '3부'])
        .annotate(grade_int=Cast('grade', IntegerField()), class_int=Cast('class_name', IntegerField()), number_int=Cast('number', IntegerField()))
        .order_by('division__division', 'grade_int', 'class_int', 'number_int', 'name')
    )


def _eval_student_rows(inst):
    """평가통지서 대상 선택 표: 학생 + 현재 단계 (단계업 기록이 없으면 기본으로 선택 해제)"""
    students = _eval_students(inst)
    cur = _current_guides(inst, students)
    groups = {}
    for st in students:                     # 1부 → 2부 → 3부 순서로 묶음
        groups.setdefault(st.division.division, []).append({
            "id": st.id, "grade": st.grade, "class_name": st.class_name, "number": st.number, "name": st.name,
            "stage": cur.get(st.id, {}).get("title", ""), "guide_id": cur.get(st.id, {}).get("id"), "checked": st.id in cur})
    return [{"division": d, "rows": groups[d]} for d in sorted(groups)]


def _fmt_ymd(d):
    return f"{d.year}. {d.month}. {d.day}."


@login_required
@require_POST
def evaluation_generate(request, institution_id):
    inst = _eval_institution(request, institution_id)
    if inst is None:
        return JsonResponse({"ok": False, "error": "접근 권한이 없습니다."}, status=403)
    try:
        year = int(request.POST.get('year'))
        semester = int(request.POST.get('semester'))
        start_m = int(request.POST.get('start_month'))
        end_m = int(request.POST.get('end_month'))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "학년도·학기·수강기간(월)을 모두 입력해주세요."}, status=400)
    if semester not in (1, 2) or not (2000 <= year <= 2100) or not (1 <= start_m <= 12 and 1 <= end_m <= 12):
        return JsonResponse({"ok": False, "error": "학년도·학기·수강기간이 올바르지 않습니다."}, status=400)
    if (end_m - 3) % 12 < (start_m - 3) % 12:       # 학년도 순서(3월~다음해 2월)로 종료월이 시작월보다 앞서면 안 됨
        return JsonResponse({"ok": False, "error": "수강기간의 종료월이 시작월보다 빠릅니다."}, status=400)

    ids = {int(x) for x in request.POST.getlist('students') if x.isdigit()}
    students = [st for st in _eval_students(inst) if st.id in ids]
    if not students:
        return JsonResponse({"ok": False, "error": "평가통지서를 만들 학생을 한 명 이상 선택해주세요."}, status=400)

    teacher = inst.teacher if (request.user.is_staff and inst.teacher_id and inst.teacher_id != request.user.id) else request.user
    teacher_name = (teacher.first_name or teacher.username).strip()
    period = f"{_school_year_of(year, start_m)}. {start_m}. ~ {_school_year_of(year, end_m)}. {end_m}."
    contents = _current_guides(inst, students)
    # 화면에서 직접 고른 단계(stage_<학생id> = 안내 id)가 있으면 그 단계의 안내 문구를 사용
    from robot_LvUP.models import LevelUpGuide
    picked = {}
    for st in students:
        gid = request.POST.get(f'stage_{st.id}', '')
        if gid.isdigit():
            g = LevelUpGuide.objects.filter(pk=int(gid)).first()
            if g:
                picked[st.id] = _guide_info(g)
    contents.update(picked)
    pages = [
        render_to_string('students/_eval_notice_page.html', {
            'year': year, 'semester': semester, 'period': period,
            'student_name': st.name, 'program': inst.program or '', 'teacher_name': teacher_name,
            'content_title': contents.get(st.id, {}).get('title', ''), 'content': contents.get(st.id, {}).get('text', ''),
        })
        for st in students
    ]
    return JsonResponse({"ok": True, "html": "".join(pages), "count": len(students), "period": period})


@login_required
@require_POST
def evaluation_save(request, institution_id):
    inst = _eval_institution(request, institution_id)
    if inst is None:
        return JsonResponse({"ok": False, "error": "접근 권한이 없습니다."}, status=403)
    try:
        payload = json.loads(request.body or b"{}")
        year = int(payload.get('year'))
        semester = int(payload.get('semester'))
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "요청을 읽지 못했습니다."}, status=400)
    html = _clean_eval_html(payload.get('html', ''))
    if len(html) < 50:
        return JsonResponse({"ok": False, "error": "저장할 내용이 없습니다."}, status=400)
    title = (payload.get('title') or f"{year}학년도 {semester}학기 평가 통지서").strip()[:120]
    fields = dict(title=title, year=year, semester=semester, period=str(payload.get('period', ''))[:60],
                  student_count=html.count('eval-page'), html=html)
    nid = payload.get('id')
    notice = EvaluationNotice.objects.filter(pk=nid, institution=inst).first() if nid else None
    if notice:
        for k, v in fields.items():
            setattr(notice, k, v)
        notice.save()
    else:
        notice = EvaluationNotice.objects.create(institution=inst, created_by=request.user, **fields)
    return JsonResponse({"ok": True, "id": notice.pk})


@login_required
def evaluation_load(request, pk):
    notice = get_object_or_404(EvaluationNotice, pk=pk)
    if not request.user.is_staff and notice.institution.teacher != request.user:
        return JsonResponse({"ok": False, "error": "접근 권한이 없습니다."}, status=403)
    return JsonResponse({"ok": True, "id": notice.pk, "title": notice.title, "year": notice.year, "semester": notice.semester,
                         "period": notice.period, "html": _clean_eval_html(notice.html),
                         "updated": timezone.localtime(notice.updated_at).strftime('%Y-%m-%d %H:%M')})


@login_required
@require_POST
def evaluation_delete(request, pk):
    notice = get_object_or_404(EvaluationNotice, pk=pk)
    if not request.user.is_staff and notice.institution.teacher != request.user:
        return JsonResponse({"ok": False, "error": "접근 권한이 없습니다."}, status=403)
    notice.delete()
    return JsonResponse({"ok": True})
