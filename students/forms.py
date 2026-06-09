from django import forms

from .models import Student

_INPUT = 'form-control'
_SELECT = 'form-select'


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'middle_name', 'phone', 'parent_phone',
            'email', 'gender', 'birth_date', 'address', 'school_name', 'grade',
            'photo', 'status', 'note',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _INPUT}),
            'last_name': forms.TextInput(attrs={'class': _INPUT}),
            'middle_name': forms.TextInput(attrs={'class': _INPUT}),
            'phone': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '+998'}),
            'parent_phone': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '+998'}),
            'email': forms.EmailInput(attrs={'class': _INPUT}),
            'gender': forms.Select(attrs={'class': _SELECT}),
            'birth_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': _INPUT}),
            'school_name': forms.TextInput(attrs={'class': _INPUT}),
            'grade': forms.TextInput(attrs={'class': _INPUT}),
            'photo': forms.FileInput(attrs={'class': _INPUT}),
            'status': forms.Select(attrs={'class': _SELECT}),
            'note': forms.Textarea(attrs={'class': _INPUT, 'rows': 2}),
        }
