from django import forms

from .models import Employee, SalaryRecord


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'full_name', 'position', 'employment_type',
            'base_salary', 'hourly_rate', 'per_student_rate',
            'kpi_bonus_pct', 'late_penalty', 'card_number', 'hire_date', 'is_active', 'note',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'per_student_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'kpi_bonus_pct': forms.NumberInput(attrs={'class': 'form-control'}),
            'late_penalty': forms.NumberInput(attrs={'class': 'form-control'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '8600 **** **** ****'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MetricsForm(forms.ModelForm):
    """Davr uchun xodim metrikalarini qo'lda tahrirlash."""

    class Meta:
        model = SalaryRecord
        fields = [
            'worked_days', 'worked_hours', 'lessons_count', 'groups_count', 'students_count',
            'attendance_rate', 'avg_score', 'late_count', 'absence_count',
            'manual_bonus', 'manual_penalty', 'metrics_note',
        ]
        widgets = {f: forms.NumberInput(attrs={'class': 'form-control'}) for f in [
            'worked_days', 'worked_hours', 'lessons_count', 'groups_count', 'students_count',
            'attendance_rate', 'avg_score', 'late_count', 'absence_count',
            'manual_bonus', 'manual_penalty',
        ]}
        widgets['metrics_note'] = forms.TextInput(attrs={'class': 'form-control'})
