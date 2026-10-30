from django.db import models
from django.db.models import JSONField
from schools.models import School

class RecruitNotice(models.Model):
    status = models.CharField(max_length=20, default="예정")  # 자동 계산용

    receive_date = models.DateField()
    deadline = models.DateTimeField()

    # 다중 선택이므로 CharField로 콤마 저장
    submit_method = models.CharField(max_length=200)

    region = models.CharField(max_length=50)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True
    )
    student_count = models.CharField(max_length=20, blank=True)

    programs = JSONField(blank=True, null=True)
    attachment_urls = JSONField(blank=True, null=True)

    # ⭐ 추가
    is_our_school = models.BooleanField(
        default=False,
        verbose_name="우리 강사 출강 학교",
        null=True
    )

from django.db import models

DAYS_OF_WEEK = [
    (1, "월"),
    (2, "화"),
    (3, "수"),
    (4, "목"),
    (5, "금"),
    (6, "토"),
]

class RecruitProgram(models.Model):
    name = models.CharField("프로그램명", max_length=100)
    day = models.IntegerField("요일", choices=DAYS_OF_WEEK)
    start_time = models.TimeField("시작 시간")
    end_time = models.TimeField("종료 시간")
    capacity = models.PositiveIntegerField("정원")

    # ✅ 과목 고정 색상
    color_class = models.CharField(
        "시간표 색상",
        max_length=30,
        default="timetable-blue",
        help_text="CSS 클래스명 (예: timetable-blue)"
    )

    def __str__(self):
        return self.name

    @property
    def current_count(self):
        """
        현재 수강 인원 (신청 테이블 기준 계산)
        """
        return self.recruitapply_set.count()


class InstructorCourseType(models.Model):
    CERT_TYPE_CHOICES = [
        ("national", "국가자격"),
        ("authorized", "국가공인"),
        ("private", "민간자격"),
        ("none", "해당없음/수료증"),
    ]

    name = models.CharField("과정명", max_length=100)
    course_intro = models.TextField("과정 소개", blank=True)
    educational_goal = models.TextField("교육 목표", blank=True)
    curriculum = models.JSONField("커리큘럼", default=list, blank=True)
    
    certificate_agency = models.CharField("발급기관", max_length=100, blank=True)
    certificate_type = models.CharField("자격증 종류", max_length=20, choices=CERT_TYPE_CHOICES, blank=True)

    cost_education = models.PositiveIntegerField("교육비", default=0)
    cost_certificate = models.PositiveIntegerField("자격발급비", default=0)
    cost_material = models.PositiveIntegerField("교재/교구비", default=0)
    cost_includes_all = models.BooleanField("비용 일체 포함 여부", default=False)
    
    benefits = models.TextField("제공혜택", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "지도사과정 유형"
        verbose_name_plural = "지도사과정 유형"
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstructorRecruit(models.Model):
    STATUS_CHOICES = [
        ("open", "모집중"),
        ("closed", "마감"),
        ("hidden", "비공개"),
    ]
    
    CERT_TYPE_CHOICES = [
        ("national", "국가자격"),
        ("authorized", "국가공인"),
        ("private", "민간자격"),
        ("none", "해당없음/수료증"),
    ]

    course_type = models.ForeignKey(
        InstructorCourseType, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name="과정 종류"
    )
    title = models.CharField("공고명", max_length=200)
    
    class_start_date = models.DateField("수업 시작일", null=True, blank=True)
    class_end_date = models.DateField("수업 종료일", null=True, blank=True)
    class_days = models.CharField("수업 요일", max_length=50, blank=True)
    class_time = models.CharField("수업 시간", max_length=100, blank=True)
    
    course_intro = models.TextField("과정 소개", blank=True)
    educational_goal = models.TextField("교육 목표", blank=True)
    curriculum = models.JSONField("커리큘럼", default=list, blank=True)
    
    certificate_agency = models.CharField("발급기관", max_length=100, blank=True)
    certificate_type = models.CharField("자격증 종류", max_length=20, choices=CERT_TYPE_CHOICES, blank=True)

    cost_education = models.PositiveIntegerField("교육비", default=0)
    cost_certificate = models.PositiveIntegerField("자격발급비", default=0)
    cost_material = models.PositiveIntegerField("교재/교구비", default=0)
    cost_includes_all = models.BooleanField("비용 일체 포함 여부", default=False)
    
    benefits = models.TextField("제공혜택", blank=True)
    
    recruit_start = models.DateTimeField("모집 시작일")
    recruit_end = models.DateTimeField("모집 마감일")
    capacity = models.PositiveIntegerField("모집 정원", default=0, help_text="0이면 제한 없음")
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default="hidden")
    image = models.ImageField("대표 이미지", upload_to="instructor_recruits/", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "지도사과정 모집 공고"
        verbose_name_plural = "지도사과정 모집 공고"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class InstructorApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "신청완료"),
        ("approved", "승인"),
        ("rejected", "반려"),
        ("cancelled", "취소"),
    ]

    recruit = models.ForeignKey(InstructorRecruit, on_delete=models.CASCADE, related_name="applications", verbose_name="공고")
    
    applicant = models.ForeignKey(
        "accounts.Profile", 
        on_delete=models.CASCADE, 
        related_name="instructor_applications", 
        null=True, blank=True, 
        verbose_name="지원자(회원)"
    )
    
    applicant_name = models.CharField("이름", max_length=100)
    phone = models.CharField("연락처", max_length=30)
    memo = models.TextField("지원동기 및 남길말", blank=True)
    
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default="pending")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "지도사과정 지원 내역"
        verbose_name_plural = "지도사과정 지원 내역"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.applicant_name} - {self.recruit.title}"


class DispatchRecruit(models.Model):
    """출강 강사 모집 공고 (관리자가 등록, 강사가 확인)"""
    STATUS_CHOICES = [("open", "모집중"), ("closed", "마감")]
    PROGRAM_CHOICES = ["AI", "로봇", "코딩", "과학", "3D펜", "항공드론", "창의수학"]
    WEEKDAYS = "월화수목금토일"

    title = models.CharField("제목", max_length=200, default="출강 가능하신 강사님 모집합니다!")
    # 일정: schedule_data = {"same": bool, "items": [{"date": "2026-08-12", "start": "09:00", "end": "16:00"}]}
    schedule_data = models.JSONField("일정·시간 데이터", null=True, blank=True)
    schedule = models.TextField("일정", blank=True)       # schedule_data 로 자동 생성되는 표시용 문구
    time_info = models.TextField("시간", blank=True)      # 〃
    place = models.CharField("장소", max_length=200, blank=True)
    place_address = models.CharField("주소", max_length=255, blank=True)
    target = models.CharField("대상", max_length=200, blank=True)
    subject = models.CharField("주제", max_length=200, blank=True)
    programs = models.JSONField("프로그램", default=list, blank=True)
    content = models.TextField("수업 내용", blank=True)
    materials = models.CharField("사용교구 및 프로그램", max_length=200, blank=True)
    pay_main = models.PositiveIntegerField("주강사 시간당 강사료", default=50000)
    pay_assist = models.PositiveIntegerField("보조강사 시간당 강사료", default=30000)
    notes = models.TextField("기타 안내", blank=True)
    deadline = models.DateField("모집 마감일", null=True, blank=True, help_text="마감일이 지나면 자동으로 마감됩니다.")
    status = models.CharField("상태", max_length=10, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]      # 모집중 → 마감 순, 최신 먼저
        verbose_name = "출강강사 모집"
        verbose_name_plural = "출강강사 모집"

    def __str__(self):
        return self.title

    @classmethod
    def close_expired(cls):
        """마감일이 지난 모집중 공고를 자동으로 마감"""
        from django.utils import timezone
        return cls.objects.filter(status="open", deadline__lt=timezone.localdate()).update(status="closed")

    @classmethod
    def auto_title(cls, place, subject):
        return " ".join(x for x in (place, subject, "강사 모집") if x).strip()

    @property
    def d_day(self):
        """마감까지 남은 일수 (마감일 없으면 None)"""
        from django.utils import timezone
        if not self.deadline:
            return None
        return (self.deadline - timezone.localdate()).days

    # ---- 표시용 문구 ----
    def _items(self):
        from datetime import date as _date
        out = []
        for it in sorted((self.schedule_data or {}).get("items", []), key=lambda x: x.get("date", "")):
            try:
                y, m, d = map(int, it["date"].split("-"))
                out.append((_date(y, m, d), it.get("start", ""), it.get("end", "")))
            except (KeyError, ValueError):
                continue
        return out

    def build_display(self):
        """schedule_data → schedule(일정 문구), time_info(시간 문구)"""
        from django.utils import timezone
        items = self._items()
        if not items:
            return
        this_year = timezone.localdate().year
        label = lambda d: f"{d.month}월 {d.day}일({self.WEEKDAYS[d.weekday()]})"
        groups, parts = {}, []
        for d, _s, _e in items:
            groups.setdefault((d.year, d.month), []).append(d)
        for (y, m), ds in groups.items():
            head = f"{y}년 " if y != this_year else ""
            parts.append(head + f"{m}월 " + ", ".join(f"{d.day}일({self.WEEKDAYS[d.weekday()]})" for d in ds))
        self.schedule = " / ".join(parts)
        times = {(s, e) for _d, s, e in items}
        if len(times) == 1:
            s, e = next(iter(times))
            self.time_info = f"{s}~{e}"
        else:
            self.time_info = chr(10).join(f"{label(d)} {s}~{e}" for d, s, e in items)

    @property
    def program_text(self):
        return ", ".join(self.programs or [])

    @property
    def place_full(self):
        if self.place and self.place_address:
            return f"{self.place} ({self.place_address})"
        return self.place or self.place_address

    @property
    def share_text(self):
        """메신저에 붙여넣기 좋은 공고 문구"""
        lines = [self.title, ""]
        for label, value in (("일정", self.schedule), ("장소", self.place_full), ("시간", self.time_info),
                             ("대상", self.target), ("주제", self.subject), ("프로그램", self.program_text)):
            if value:
                lines.append(f"ㅇ {label} : {value}")
        if self.content:
            lines += ["", self.content]
        if self.materials:
            lines += ["", f"ㅇ 사용교구 및 프로그램 : {self.materials}"]
        lines += ["", "ㅇ 강사료 (시간당)",
                  f"  주강사 : {self.pay_main:,}원", f"  보조강사 : {self.pay_assist:,}원"]
        if self.deadline:
            lines += ["", f"ㅇ 모집 마감 : {self.deadline.year}.{self.deadline.month}.{self.deadline.day}"]
        if self.notes:
            lines += ["", self.notes]
        return chr(10).join(lines)


class DispatchApplication(models.Model):
    """출강강사 모집 지원 내역"""
    ROLE_CHOICES = [("main", "주강사"), ("assist", "보조강사"), ("any", "상관없음")]
    STATUS_CHOICES = [("pending", "대기"), ("approved", "승인"), ("rejected", "반려")]

    recruit = models.ForeignKey(DispatchRecruit, on_delete=models.CASCADE, related_name="applications")
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="dispatch_applications")
    role = models.CharField("지원 구분", max_length=10, choices=ROLE_CHOICES, default="any")
    memo = models.CharField("전달 사항", max_length=300, blank=True)
    status = models.CharField("상태", max_length=10, choices=STATUS_CHOICES, default="pending")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["applied_at"]
        unique_together = ("recruit", "user")
        verbose_name = "출강강사 지원"
        verbose_name_plural = "출강강사 지원"

    def __str__(self):
        return f"{self.user} → {self.recruit}"
