from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    USER_TYPES = (
        ('student', '학생'),
        ('parent', '학부모'),
        ("pre_teacher", "예비강사"),
        ('teacher', '강사'),
        ('center_teacher', '센터강사'),
        ('institution', '기관'),
    )
    # 현재 모집·관리 대상(가입·회원목록 화면에서 선택 가능한 유형). 나머지 유형은 기존 회원 데이터 때문에만 남겨 둠
    ACTIVE_USER_TYPES = (
        ("teacher", "강사"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='parent')
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    postcode = models.CharField(max_length=10, blank=True)
    address = models.CharField(max_length=255, blank=True)
    detail_address = models.CharField(max_length=255, blank=True)

    # ✅ 카카오 연동 필드
    kakao_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    kakao_name = models.CharField(max_length=100, null=True, blank=True)  # 카카오 닉네임 저장

    # ✅ 탈퇴 상태
    withdrawal_requested = models.BooleanField(default=False)

    # ✅ 계정 정지 (장기 미접속·미거래) - 정지되면 User.is_active 도 False 가 되어 로그인이 막힘
    suspended_at = models.DateTimeField("정지일시", null=True, blank=True)
    suspend_reason = models.CharField("정지 사유", max_length=200, blank=True)

    def __str__(self):
        return f'{self.user.username} 프로필'
    
class Child(models.Model):
    parent = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="children")
    name = models.CharField("자녀 이름", max_length=50)
    birth_date = models.DateField("자녀 생년월일")

    # ⭐ 추가 (학생 회원 계정 연결)
    student_profile = models.OneToOneField(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_student",
        verbose_name="학생 계정"
    )

    def __str__(self):
        return f"{self.parent.user.username} - {self.name}"


class KakaoToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField(default="")   # ✅ 기본값 추가
    expires_in = models.IntegerField(default=0)
    refresh_token_expires_in = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.access_token[:10]}..."
    
from django.db import models
from django.contrib.auth.models import User


class InstitutionProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='institution_profile'
    )

    # 기관 기본
    institution_name = models.CharField('기관명', max_length=120)
    business_number  = models.CharField('사업자등록번호', max_length=30, blank=True)

    # 담당자
    contact_name     = models.CharField('담당자명', max_length=60)
    contact_phone    = models.CharField('담당자 휴대폰 번호', max_length=30, blank=True)

    # 기관 연락처
    office_phone     = models.CharField('기관 전화번호', max_length=30, blank=True)
    fax              = models.CharField('팩스', max_length=30, blank=True)

    # 주소
    postcode         = models.CharField('우편번호', max_length=16, blank=True)
    address          = models.CharField('주소', max_length=255, blank=True)
    detail_address   = models.CharField('상세주소', max_length=255, blank=True)

    # 추가 정보
    industry         = models.CharField('업종', max_length=60, blank=True)
    website          = models.URLField('홈페이지', blank=True)
    note             = models.TextField('비고', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.institution_name


class AdminSeen(models.Model):
    """관리자가 승인/정지 화면을 마지막으로 확인한 시각 - 메뉴의 '새로 추가된 수' 계산용"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=30)          # approve / suspended
    seen_at = models.DateTimeField()

    class Meta:
        unique_together = ("user", "key")
