from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Course, Subject

_INPUT = 'form-control'
_SELECT = 'form-select'


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description', 'color', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': _INPUT}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'name', 'subject', 'level', 'teacher', 'description', 'monthly_fee',
            'duration_months', 'capacity', 'weekdays', 'start_time',
            'room', 'start_date', 'status',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': _('Masalan: Ingliz tili — kechki guruh')}),
            'subject': forms.Select(attrs={'class': _SELECT}),
            'level': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Beginner / A1 / Intermediate ...'}),
            'teacher': forms.Select(attrs={'class': _SELECT}),
            'description': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
            'monthly_fee': forms.NumberInput(attrs={'class': _INPUT, 'step': '1000'}),
            'duration_months': forms.NumberInput(attrs={'class': _INPUT}),
            'capacity': forms.NumberInput(attrs={'class': _INPUT}),
            'weekdays': forms.Select(attrs={'class': _SELECT}),
            'start_time': forms.TimeInput(attrs={'class': _INPUT, 'type': 'time'}),
            'room': forms.TextInput(attrs={'class': _INPUT}),
            'start_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'status': forms.Select(attrs={'class': _SELECT}),
        }
