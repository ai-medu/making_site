# teachers/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import TeachingInstitution, TeachingDay, Certificate, Career, Education
from schools.models import School

class TeachingInstitutionForm(forms.ModelForm):

    teacher_choice = forms.ChoiceField(
        required=False,
        label="강사 선택"
    )

    # 🔥 학교 FK (JS로 값 채움)
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )

    days = forms.ModelMultipleChoiceField(
        queryset=TeachingDay.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="출강 요일"
    )

    class Meta:
        model = TeachingInstitution
        fields = [
            "place_type",     # ✅ 모델 필드 그대로 사용
            "school",
            "name",
            "program",
            "days",
            "contact_email",
            "admin_email",
        ]
        widgets = {
            "place_type": forms.RadioSelect,   # ⭐ 여기서만 widget 지정
            "contact_email": forms.EmailInput(attrs={
                "placeholder": "ex) teacher@school.kr",
                "autocomplete": "email"
            }),
            "admin_email": forms.EmailInput(attrs={
                "placeholder": "ex) admin@school.kr",
                "autocomplete": "email"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        teachers = User.objects.filter(profile__user_type='teacher').order_by('first_name')
        center_teachers = User.objects.filter(profile__user_type='center_teacher').order_by('first_name')

        self.fields['teacher_choice'].choices = [
            ('강사', [(u.id, f"{u.first_name} ({u.username})") for u in teachers]),
            ('센터강사', [(u.id, f"{u.first_name} ({u.username})") for u in center_teachers]),
        ]


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['cert_type', 'name', 'issued_by', 'issued_date', 'expires_date']
        widgets = {
            'issued_date': forms.DateInput(attrs={'type': 'date'}),
            'expires_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 새로 등록·수정할 때는 자격 종류를 반드시 고르게 함 (이전에 등록된 자격증은 비어 있을 수 있음)
        f = self.fields['cert_type']
        f.required = True
        f.choices = [('', '선택하세요')] + list(Certificate.TYPE_CHOICES)

class CareerForm(forms.ModelForm):
    # 종료일이 없으면 '현재'(재직 중)로 취급한다. 체크하면 종료일을 비우고 현재로 저장.
    is_current = forms.BooleanField(required=False, label="현재")

    class Meta:
        model = Career
        fields = ['organization', 'position', 'start_date', 'end_date', 'description']
        labels = {'position': '프로그램명'}
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.end_date is None and not self.is_bound:
            self.initial['is_current'] = True

    def clean(self):
        data = super().clean()
        start, end = data.get('start_date'), data.get('end_date')
        if data.get('is_current'):
            data['end_date'] = None
            self.errors.pop('end_date', None)
        elif not end:
            if 'end_date' not in self.errors:
                self.add_error('end_date', "종료일을 입력하거나 '현재'를 체크해주세요.")
        elif start and end < start:
            self.add_error('end_date', "종료일이 시작일보다 빠릅니다.")
        return data

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['school_name', 'status', 'major', 'degree', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
