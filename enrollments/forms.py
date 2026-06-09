from django import forms
from django.utils.translation import gettext_lazy as _

from courses.models import Course, Subject

from .models import Enrollment, RegistrationApplication

_INPUT = 'form-control'
_SELECT = 'form-select'


class PublicApplicationForm(forms.ModelForm):
    """Ommaviy onlayn ariza formasi (landing sahifa)."""

    class Meta:
        model = RegistrationApplication
        fields = ['full_name', 'phone', 'parent_phone', 'age', 'subject', 'source', 'message']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': _('Ism Familiya')}),
            'phone': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '+998 90 123 45 67'}),
            'parent_phone': forms.TextInput(attrs={'class': _INPUT, 'placeholder': _('+998 (ixtiyoriy)')}),
            'age': forms.NumberInput(attrs={'class': _INPUT, 'placeholder': _('Yosh')}),
            'subject': forms.Select(attrs={'class': _SELECT}),
            'source': forms.Select(attrs={'class': _SELECT}),
            'message': forms.Textarea(attrs={'class': _INPUT, 'rows': 3, 'placeholder': _("Qo'shimcha izoh")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)
        self.fields['subject'].empty_label = _("Yo'nalishni tanlang")


class ApplicationStatusForm(forms.ModelForm):
    """Xodim arizani qayta ishlashi."""

    class Meta:
        model = RegistrationApplication
        fields = ['status', 'assigned_to', 'preferred_course', 'staff_note']
        widgets = {
            'status': forms.Select(attrs={'class': _SELECT}),
            'assigned_to': forms.Select(attrs={'class': _SELECT}),
            'preferred_course': forms.Select(attrs={'class': _SELECT}),
            'staff_note': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
        }


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'monthly_fee', 'discount_percent', 'start_date', 'status']
        widgets = {
            'student': forms.Select(attrs={'class': _SELECT}),
            'course': forms.Select(attrs={'class': _SELECT}),
            'monthly_fee': forms.NumberInput(attrs={'class': _INPUT, 'step': '1000'}),
            'discount_percent': forms.NumberInput(attrs={'class': _INPUT}),
            'start_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'status': forms.Select(attrs={'class': _SELECT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.exclude(status='finished')
        self.fields['monthly_fee'].required = False
