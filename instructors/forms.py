from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Instructor

User = get_user_model()

_INPUT = {'class': 'form-control'}


def suggest_teacher_username(first_name, last_name):
    """O'qituvchi uchun band bo'lmagan unikal login tavsiya qiladi."""
    base = (slugify(f"{first_name}{last_name}") or 'teacher').replace('-', '')[:20] or 'teacher'
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base}{i}"
    return username


class InstructorCreateForm(forms.Form):
    """Yangi o'qituvchi + kabinet logini yaratish formasi.

    O'qituvchi `role='teacher'` foydalanuvchi sifatida yaratiladi — signal
    avtomatik `Instructor` profilini hosil qiladi, view uni to'ldiradi.
    """

    first_name = forms.CharField(
        label=_("Ism"), max_length=150,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': _('Ism')}))
    last_name = forms.CharField(
        label=_("Familiya"), max_length=150, required=False,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': _('Familiya')}))
    phone = forms.CharField(
        label=_("Telefon"), max_length=20, required=False,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': '+998 90 123 45 67'}))
    email = forms.EmailField(
        label=_("Email"), required=False,
        widget=forms.EmailInput(attrs={**_INPUT, 'placeholder': 'email@example.com'}))
    specialty = forms.CharField(
        label=_("Mutaxassislik / fan"), max_length=255, required=False,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': _('Masalan: Matematika')}))
    experience_years = forms.IntegerField(
        label=_("Tajriba (yil)"), required=False, min_value=0, initial=0,
        widget=forms.NumberInput(attrs={**_INPUT, 'placeholder': '0'}))
    salary = forms.DecimalField(
        label=_("Oylik (so'm)"), required=False, min_value=0, initial=0,
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={**_INPUT, 'placeholder': '0'}))
    bio = forms.CharField(
        label=_("Qisqacha ma'lumot"), required=False,
        widget=forms.Textarea(attrs={**_INPUT, 'rows': 3, 'placeholder': _('Bio (ixtiyoriy)')}))
    image = forms.ImageField(
        label=_("Rasm"), required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    username = forms.CharField(
        label=_("Login (username)"), max_length=150, required=False,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': _("Bo'sh — avtomatik")}))
    password = forms.CharField(
        label=_("Parol"), max_length=128, required=False,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': _("Bo'sh — avtomatik xavfsiz parol")}))

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("Bu login band — boshqasini tanlang yoki bo'sh qoldiring."))
        return username


class InstructorUpdateForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = [
            'full_name',
            'phone',
            'email',
            'specialty',
            'experience_years',
            'salary',
            'bio',
            'image',
            'is_active',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('To‘liq ism')}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Telefon')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email')}),
            'specialty': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mutaxassislik')}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Tajriba yili')}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Oylik')}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Qisqacha ma’lumot')}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
