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
        fields = ['name', 'issued_by', 'issued_date', 'expires_date']
        widgets = {
            'issued_date': forms.DateInput(attrs={'type': 'date'}),
            'expires_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CareerForm(forms.ModelForm):
    class Meta:
        model = Career
        fields = ['organization', 'position', 'start_date', 'end_date', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['school_name', 'status', 'major', 'degree', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
