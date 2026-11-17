from django import forms
from .models import RobotLevelUp, LevelUpGuide
from materials.models import Material

class RobotLevelUpForm(forms.ModelForm):
    class Meta:
        model = RobotLevelUp
        fields = [
            'year_month', 'material', 'section',
            'grade', 'class_no', 'student_no', 'student_name',
            'price', 'note'
        ]
        widgets = {
            'year_month': forms.TextInput(attrs={'type': 'month', 'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'grade': forms.NumberInput(attrs={'class': 'form-control'}),
            'class_no': forms.NumberInput(attrs={'class': 'form-control'}),
            'student_no': forms.NumberInput(attrs={'class': 'form-control'}),
            'student_name': forms.TextInput(attrs={'class': 'form-control'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # '로봇' 카테고리 교구만 선택 가능
        self.fields['material'].queryset = Material.objects.filter(vendor__vendor_type__name='로봇')
        self.fields['material'].widget.attrs.update({'class': 'form-select'})



class LevelUpGuideForm(forms.ModelForm):
    class Meta:
        model = LevelUpGuide
        fields = ["robot", "stage", "text", "order"]
        widgets = {
            "robot": forms.Select(attrs={"class": "form-select"}),
            "stage": forms.TextInput(attrs={"class": "form-control", "placeholder": "예: 1단계, SD단계"}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 6, "id": "guideText"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }
        help_texts = {"order": "같은 로봇 안에서 작은 숫자가 먼저 나옵니다. 비워 두면 맨 뒤에 추가됩니다."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].required = False

    def clean_order(self):
        order = self.cleaned_data.get("order")
        if order is None:
            last = LevelUpGuide.objects.filter(robot=self.cleaned_data.get("robot")).order_by("-order").first()
            order = (last.order + 1) if last else 1
        return order
