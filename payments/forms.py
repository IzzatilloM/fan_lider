from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from students.models import Student

from .models import Invoice, Payment, UZB_MONTHS

_INPUT = 'form-control'
_SELECT = 'form-select'

MONTH_CHOICES = [(i + 1, name) for i, name in enumerate(UZB_MONTHS)]


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['student', 'invoice', 'amount', 'method', 'paid_at', 'note']
        widgets = {
            'student': forms.Select(attrs={'class': _SELECT}),
            'invoice': forms.Select(attrs={'class': _SELECT}),
            'amount': forms.NumberInput(attrs={'class': _INPUT, 'step': '1000'}),
            'method': forms.Select(attrs={'class': _SELECT}),
            'paid_at': forms.DateTimeInput(
                attrs={'class': _INPUT, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'note': forms.TextInput(attrs={'class': _INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paid_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
        self.fields['invoice'].required = False
        self.fields['invoice'].queryset = Invoice.objects.exclude(
            status__in=['paid', 'cancelled']
        ).select_related('student')
        self.fields['student'].queryset = Student.objects.filter(status='active')


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['student', 'enrollment', 'course', 'year', 'month', 'amount', 'due_date', 'status']
        widgets = {
            'student': forms.Select(attrs={'class': _SELECT}),
            'enrollment': forms.Select(attrs={'class': _SELECT}),
            'course': forms.Select(attrs={'class': _SELECT}),
            'year': forms.NumberInput(attrs={'class': _INPUT}),
            'month': forms.Select(attrs={'class': _SELECT}, choices=MONTH_CHOICES),
            'amount': forms.NumberInput(attrs={'class': _INPUT, 'step': '1000'}),
            'due_date': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
            'status': forms.Select(attrs={'class': _SELECT}),
        }


class GenerateInvoicesForm(forms.Form):
    """Tanlangan oy uchun barcha faol yozilishlarga hisob-faktura yaratish."""
    year = forms.IntegerField(
        label=_("Yil"), initial=timezone.now().year,
        widget=forms.NumberInput(attrs={'class': _INPUT}),
    )
    month = forms.ChoiceField(
        label=_("Oy"), choices=MONTH_CHOICES, initial=timezone.now().month,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    due_day = forms.IntegerField(
        label=_("To'lov muddati (oyning kuni)"), initial=10, min_value=1, max_value=28,
        widget=forms.NumberInput(attrs={'class': _INPUT}),
    )
