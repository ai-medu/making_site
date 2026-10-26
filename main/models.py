from django.db import models

class MenuItem(models.Model):
    ACCESS_LEVELS = (
        ('all', '누구나'),
        ('teacher', '강사용'),
        ('institution', '기관용'),
        ('staff', '관리자용'),
    )

    title = models.CharField("메뉴 제목", max_length=100)
    url = models.CharField("이동 URL/뷰이름", max_length=255, blank=True, default="#")
    icon_class = models.CharField("아이콘 클래스", max_length=100, blank=True, help_text="예: bi-gear, bi-people")
    order = models.PositiveIntegerField("출력 순서", default=0)
    is_active = models.BooleanField("활성화 상태", default=True)
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sub_menus',
        verbose_name="상위 메뉴"
    )
    
    access_level = models.CharField(
        "접근 권한", 
        max_length=20, 
        choices=ACCESS_LEVELS, 
        default='staff'
    )

    class Meta:
        verbose_name = "메뉴 항목"
        verbose_name_plural = "메뉴 항목들"
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.title} ({self.get_access_level_display()})"



class AIApiKey(models.Model):
    """관리자가 등록하는 AI API 키 (여러 개 등록, 사용 중인 키 순서대로 사용)"""
    PROVIDER_CHOICES = [
        ("gemini", "Google Gemini"),
    ]

    name = models.CharField("이름", max_length=100, help_text="구분하기 위한 이름 (예: 메인 키, 예비 키)")
    provider = models.CharField("서비스", max_length=20, choices=PROVIDER_CHOICES, default="gemini")
    api_key = models.CharField("API 키", max_length=255)
    is_active = models.BooleanField("사용", default=True)
    order = models.PositiveIntegerField("사용 순서", default=0, help_text="작은 숫자부터 먼저 사용합니다. 사용량이 초과되면 다음 키를 사용합니다.")
    memo = models.CharField("메모", max_length=200, blank=True)

    success_count = models.PositiveIntegerField("성공 횟수", default=0)
    fail_count = models.PositiveIntegerField("실패 횟수", default=0)
    last_used_at = models.DateTimeField("마지막 사용", null=True, blank=True)
    last_error = models.CharField("마지막 오류", max_length=300, blank=True)
    last_error_at = models.DateTimeField("마지막 오류 시각", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "AI API 키"
        verbose_name_plural = "AI API 키"

    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"

    @property
    def masked_key(self):
        k = self.api_key or ""
        if len(k) <= 10:
            return "*" * len(k)
        return f"{k[:4]}{'*' * 8}{k[-4:]}"
