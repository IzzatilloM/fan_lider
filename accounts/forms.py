from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _

from .models import CustomUser

User = get_user_model()

_input = lambda ph='', **kw: forms.TextInput(attrs={'class': 'form-control', 'placeholder': ph, **kw})


class RegisterForm(forms.Form):
    """1-qadam: ro'yxatdan o'tish ma'lumotlari. Tasdiqlash kodi Telegram bot
    orqali (chat_id ga) yuboriladi.

    Faqat Administrator yoki Direktor o'zini ro'yxatdan o'tkaza oladi.
    """

    role = forms.ChoiceField(
        label=_("Lavozim"),
        choices=(('admin', _('Administrator')), ('director', _('Direktor'))),
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
    )
    first_name = forms.CharField(
        label=_("Ism"), max_length=150,
        widget=_input(_("Ismingiz")),
    )
    last_name = forms.CharField(
        label=_("Familiya"), max_length=150, required=False,
        widget=_input(_("Familiyangiz")),
    )
    username = forms.CharField(
        label=_("Login"), max_length=150,
        widget=_input(_("login (keyin shu bilan kirasiz)"), autocomplete='username'),
        help_text=_("Tizimga kirish uchun login. Faqat harf, raqam va _ belgisi."),
    )
    telegram_chat_id = forms.CharField(
        label=_("Telegram ID"),
        widget=_input(_("Botdan olingan ID raqami"), inputmode='numeric'),
        help_text=_("Botni oching va «🆔 ID raqamim» tugmasini bosib, raqamni shu yerga kiriting."),
    )
    phone = forms.CharField(
        label=_("Telefon"), max_length=20, required=False,
        widget=_input("+998 90 123 45 67"),
    )
    password1 = forms.CharField(
        label=_("Parol"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Kamida 6 ta belgi"), 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label=_("Parolni takrorlang"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Parolni qayta kiriting"), 'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Faqat bo'sh joyi bor rollarni ko'rsatamiz
        from .utils import available_register_roles
        roles = available_register_roles()
        if roles:
            self.fields['role'].choices = roles
            self.fields['role'].initial = roles[0][0]

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError(_("Login majburiy."))
        if not all(c.isalnum() or c == '_' for c in username):
            raise forms.ValidationError(_("Login faqat harf, raqam va _ belgisidan iborat bo'lsin."))
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("Bu login band. Boshqasini tanlang."))
        return username

    def clean_telegram_chat_id(self):
        chat_id = (self.cleaned_data.get('telegram_chat_id') or '').strip()
        if not chat_id:
            raise forms.ValidationError(_("Telegram ID raqamingizni kiriting."))
        if not chat_id.lstrip('-').isdigit():
            raise forms.ValidationError(_("Telegram ID faqat raqamlardan iborat (botdan oling)."))
        return chat_id

    def clean_role(self):
        from .utils import admin_slots_left, director_slots_left
        role = self.cleaned_data.get('role')
        if role == 'director' and director_slots_left() <= 0:
            raise forms.ValidationError(_("Direktor allaqachon mavjud. Yangi direktor qo'sha olmaysiz."))
        if role == 'admin' and admin_slots_left() <= 0:
            raise forms.ValidationError(_("Administratorlar soni to'lgan."))
        return role

    def clean(self):
        cleaned = super().clean()

        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _("Parollar mos kelmadi."))
        if p1:
            try:
                password_validation.validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned


class LoginForm(forms.Form):
    """Tizimga kirish. Foydalanuvchi rolini tanlab (admin/direktor/o'qituvchi/
    o'quvchi), login + parol bilan kiradi. Tanlangan rol hisobga mos kelishi
    tekshiriladi."""

    ROLE_CHOICES = (
        ('admin', _('Administrator')),
        ('director', _('Direktor')),
        ('teacher', _("O'qituvchi")),
        ('student', _("O'quvchi")),
    )

    role = forms.ChoiceField(
        label=_("Rol"),
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
        initial='teacher',
        required=False,
    )
    identifier = forms.CharField(
        label=_("Login"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Loginingiz (yoki email)'), 'autocomplete': 'username', 'autofocus': True}),
    )
    password = forms.CharField(
        label=_("Parol"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Parolingiz'), 'autocomplete': 'current-password'}),
    )


class CodeForm(forms.Form):
    code = forms.CharField(
        label=_("Tasdiqlash kodi"), min_length=6, max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control code-input', 'placeholder': '______',
            'inputmode': 'numeric', 'autocomplete': 'one-time-code',
            'pattern': '[0-9]*', 'maxlength': '6', 'autofocus': True,
        }),
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("Kod faqat raqamlardan iborat."))
        return code


class ForgotForm(forms.Form):
    """Admin/direktor parolni tiklaydi: Telegram ID yoki Gmail kiritadi —
    tasdiqlash kodi tanlangan kanal orqali yuboriladi."""

    channel = forms.ChoiceField(
        label=_("Tasdiqlash usuli"),
        choices=(('telegram', _('Telegram bot')), ('email', _('Gmail'))),
        initial='telegram', required=False,
        widget=forms.RadioSelect(attrs={'class': 'channel-radio'}),
    )
    telegram_chat_id = forms.CharField(
        label=_("Telegram ID"), required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': _('Botdan olingan ID raqami'),
            'inputmode': 'numeric',
        }),
    )
    email = forms.EmailField(
        label=_("Email (Gmail)"), required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'sizning@gmail.com',
            'autocomplete': 'email',
        }),
    )

    def clean_telegram_chat_id(self):
        chat_id = (self.cleaned_data.get('telegram_chat_id') or '').strip()
        if chat_id and not chat_id.lstrip('-').isdigit():
            raise forms.ValidationError(_("Telegram ID faqat raqamlardan iborat."))
        return chat_id

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()

    def clean(self):
        cleaned = super().clean()
        channel = cleaned.get('channel') or 'telegram'
        cleaned['channel'] = channel
        if channel == 'email' and not cleaned.get('email'):
            self.add_error('email', _("Email manzilingizni kiriting."))
        elif channel == 'telegram' and not cleaned.get('telegram_chat_id'):
            self.add_error('telegram_chat_id', _("Telegram ID raqamingizni kiriting."))
        return cleaned


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label=_("Yangi parol"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Kamida 6 ta belgi"), 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label=_("Parolni takrorlang"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Parolni qayta kiriting"), 'autocomplete': 'new-password'}),
    )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _("Parollar mos kelmadi."))
        if p1:
            try:
                password_validation.validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998 90 123 45 67'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class UserRoleForm(forms.ModelForm):
    """Administrator foydalanuvchi rolini boshqaradi."""

    class Meta:
        model = CustomUser
        fields = ['role', 'phone', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AdminUserForm(forms.ModelForm):
    """Admin tomonidan foydalanuvchi (o'qituvchi/o'quvchi/direktor/admin) yaratish/tahrirlash.

    Parol ochiq saqlanadi (`plain_password`) — admin keyin ko'ra oladi.
    """

    password = forms.CharField(
        label=_("Parol"), required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Bo'sh qoldirilsa — avtomatik / o'zgarmaydi")}),
        help_text=_("Yangi foydalanuvchi uchun majburiy. Tahrirda bo'sh = parol o'zgarmaydi."),
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'phone',
                  'telegram_chat_id', 'role', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Ism')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Familiya')}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'login'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('email (ixtiyoriy)')}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998 ...'}),
            'telegram_chat_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Telegram ID (ixtiyoriy)')}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        # Tahrirda username o'zgartirilsa ham unikal bo'lishi nazorat qilinadi (clean_username)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError(_("Login (username) majburiy."))
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Bu login band. Boshqasini tanlang."))
        return username

    def clean(self):
        cleaned = super().clean()
        # Yangi foydalanuvchi uchun parol majburiy
        if not (self.instance and self.instance.pk) and not (cleaned.get('password') or '').strip():
            self.add_error('password', _("Yangi foydalanuvchi uchun parol majburiy."))
        return cleaned


class ChangeOwnPasswordForm(forms.Form):
    """Admin/xodim o'z parolini o'zgartiradi (joriy parolni tasdiqlab)."""

    current_password = forms.CharField(
        label=_("Joriy parol"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Hozirgi parolingiz'), 'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label=_("Yangi parol"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Kamida 6 ta belgi"), 'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label=_("Yangi parolni takrorlang"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Parolni qayta kiriting"), 'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        cur = self.cleaned_data.get('current_password') or ''
        if self.user and not self.user.check_password(cur):
            raise forms.ValidationError(_("Joriy parol noto'g'ri."))
        return cur

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('new_password1'), cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', _("Yangi parollar mos kelmadi."))
        if p1:
            try:
                password_validation.validate_password(p1, self.user)
            except forms.ValidationError as e:
                self.add_error('new_password1', e)
        return cleaned


class CenterProfileForm(forms.ModelForm):
    """O'quv markazi ma'lumotlari (Sozlamalar sahifasi)."""

    class Meta:
        from dashboard.models import CenterProfile
        model = CenterProfile
        fields = ['name', 'tagline', 'phone', 'email', 'address',
                  'working_hours', 'telegram_bot_username', 'about', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'working_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_bot_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fan_lider_crm_bot'}),
            'about': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
