"""Hisob oqimi: ro'yxatdan o'tish (Telegram kodi bilan), kirish, parolni tiklash."""
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import (
    AdminUserForm, CenterProfileForm, ChangeOwnPasswordForm, CodeForm, ForgotForm,
    LoginForm, ProfileForm, RegisterForm, ResetPasswordForm,
)
from .models import PasswordResetRequest, TelegramVerificationCode
from .utils import admin_login_allowed, apply_role_for_new_user, send_verification

User = get_user_model()

logger = logging.getLogger(__name__)

PENDING_CHAT = 'pending_chat_id'        # tasdiqlanayotgan identifikator (chat_id yoki email)
PENDING_CHANNEL = 'pending_channel'     # 'telegram' yoki 'email'
PENDING_PURPOSE = 'pending_purpose'
LAST_SENT = 'code_last_sent'
RESET_OK = 'reset_chat_verified'        # tasdiqlangan identifikator
RESET_CHANNEL = 'reset_channel'


# --------------------------------------------------------------------------- #
#  Kirish
# --------------------------------------------------------------------------- #
def login_page(request):
    if request.user.is_authenticated:
        return redirect(request.user.role_home_url)

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        selected_role = form.cleaned_data.get('role')
        user = authenticate(
            request,
            username=form.cleaned_data['identifier'],
            password=form.cleaned_data['password'],
        )
        role_labels = dict(form.fields['role'].choices)
        # Superuser har doim "Administrator" rolini tanlab kira oladi (zaxira).
        role_ok = (
            not selected_role
            or user is not None and (
                user.role == selected_role
                or (user.is_superuser and selected_role == 'admin')
            )
        )
        if user is None:
            messages.error(request, _("Login yoki parol noto'g'ri."))
        elif not user.is_active:
            messages.error(request, _("Hisobingiz faollashtirilmagan. Administratorga murojaat qiling."))
        elif not role_ok:
            messages.error(
                request,
                _("Siz «%(role)s» sifatida ro'yxatdan o'tmagansiz. Iltimos, to'g'ri rolni tanlang.")
                % {'role': role_labels.get(selected_role, selected_role)},
            )
        elif not admin_login_allowed(user):
            limit = getattr(settings, 'MAX_ADMINS', 3)
            messages.error(
                request,
                _("Administratorlar soni cheklangan (%(limit)s ta). "
                  "Siz ushbu hisob bilan administrator sifatida kira olmaysiz.")
                % {'limit': limit},
            )
        else:
            login(request, user)
            # Admin parolni reset qilgan bo'lsa — majburiy yangilash modali
            if user.must_change_password:
                messages.info(request, _("Xavfsizlik uchun yangi parol o'rnating."))
                return redirect('accounts:force_password')
            messages.success(request, _("Xush kelibsiz, %(name)s!") % {'name': user.display_name})
            return redirect(request.GET.get('next') or user.role_home_url)

    return render(request, 'accounts/login.html', {'form': form})


# --------------------------------------------------------------------------- #
#  Ro'yxatdan o'tish (1-qadam: ma'lumot + kod yuborish)
# --------------------------------------------------------------------------- #
def register(request):
    if request.user.is_authenticated:
        return redirect(request.user.role_home_url)

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        chat_id = cd['telegram_chat_id']
        payload = {
            'first_name': cd['first_name'],
            'last_name': cd.get('last_name', ''),
            'username': cd['username'],
            'phone': cd.get('phone', ''),
            'role': cd.get('role', 'admin'),
            'channel': 'telegram',
            'telegram_chat_id': chat_id,
            'email': '',
            # Parolni ochiq saqlamaymiz — faqat hash
            'password': make_password(cd['password1']),
        }
        verification = TelegramVerificationCode.issue(chat_id, 'signup', payload, channel='telegram')
        try:
            sent = send_verification(verification)
        except Exception:
            logger.exception("Ro'yxatdan o'tish kodini yuborib bo'lmadi: %s", chat_id)
            sent = False
        if not sent:
            messages.error(
                request,
                _("Kod yuborilmadi. Botni oching, «🆔 ID raqamim» tugmasini bosib, "
                  "ID raqamingiz to'g'ri ekanini tekshiring va qaytadan urinib ko'ring."),
            )
            return render(request, 'accounts/register.html', {'form': form})

        request.session[PENDING_CHAT] = chat_id
        request.session[PENDING_CHANNEL] = 'telegram'
        request.session[PENDING_PURPOSE] = 'signup'
        request.session[LAST_SENT] = timezone.now().timestamp()
        messages.info(request, _("Tasdiqlash kodi Telegram botingizga yuborildi."))
        return redirect('accounts:verify')

    return render(request, 'accounts/register.html', {'form': form})


# --------------------------------------------------------------------------- #
#  Tasdiqlash kodi (2-qadam)
# --------------------------------------------------------------------------- #
def verify(request):
    identifier = request.session.get(PENDING_CHAT)
    channel = request.session.get(PENDING_CHANNEL, 'telegram')
    purpose = request.session.get(PENDING_PURPOSE, 'signup')
    if not identifier:
        messages.warning(request, _("Avval ro'yxatdan o'ting."))
        return redirect('accounts:register')

    form = CodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        verification = TelegramVerificationCode.latest_for(identifier, purpose, channel)
        if verification is None or not verification.is_valid:
            messages.error(request, _("Kod eskirgan yoki topilmadi. Qaytadan yuboring."))
        elif verification.code != form.cleaned_data['code']:
            verification.attempts += 1
            verification.save(update_fields=['attempts'])
            left = max(getattr(settings, 'TG_CODE_MAX_ATTEMPTS', 5) - verification.attempts, 0)
            messages.error(request, _("Kod noto'g'ri. Qolgan urinishlar: %(left)s.") % {'left': left})
        else:
            verification.is_used = True
            verification.save(update_fields=['is_used'])
            return _complete_verification(request, verification)

    return render(request, 'accounts/verify.html', {
        'form': form, 'identifier': identifier, 'channel': channel, 'purpose': purpose,
        'resend_seconds': getattr(settings, 'TG_CODE_RESEND_SECONDS', 60),
    })


def _complete_verification(request, verification):
    identifier = verification.email if verification.channel == 'email' else verification.chat_id
    if verification.purpose == 'signup':
        data = verification.payload or {}
        username = data.get('username') or f"user{identifier}"
        user = User(
            username=username,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            telegram_chat_id=data.get('telegram_chat_id', ''),
            is_verified=True,
        )
        user.password = data.get('password', '')  # allaqachon hashlangan
        apply_role_for_new_user(user, requested_role=data.get('role'))
        user.save()

        for key in (PENDING_CHAT, PENDING_CHANNEL, PENDING_PURPOSE, LAST_SENT):
            request.session.pop(key, None)

        login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
        messages.success(
            request,
            _("Hisobingiz yaratildi. Login: %(username)s. "
              "Siz %(role)s sifatida kirdingiz.")
            % {'username': user.username, 'role': user.get_role_display()},
        )
        return redirect(user.role_home_url)

    # reset
    request.session[RESET_OK] = identifier
    request.session[RESET_CHANNEL] = verification.channel
    request.session.pop(PENDING_PURPOSE, None)
    messages.success(request, _("Tasdiqlandi. Endi yangi parol o'rnating."))
    return redirect('accounts:reset_password')


def resend_code(request):
    identifier = request.session.get(PENDING_CHAT)
    channel = request.session.get(PENDING_CHANNEL, 'telegram')
    purpose = request.session.get(PENDING_PURPOSE, 'signup')
    if not identifier:
        return redirect('accounts:register')

    wait = getattr(settings, 'TG_CODE_RESEND_SECONDS', 60)
    last = request.session.get(LAST_SENT)
    if last and (timezone.now().timestamp() - last) < wait:
        remaining = int(wait - (timezone.now().timestamp() - last))
        messages.warning(request, _("Iltimos, %(seconds)s soniyadan so'ng qayta urining.") % {'seconds': remaining})
        return redirect('accounts:verify')

    # Eski koddan payload ni saqlab qolamiz (signup uchun)
    field = 'email' if channel == 'email' else 'chat_id'
    prev = (
        TelegramVerificationCode.objects
        .filter(purpose=purpose, channel=channel, **{field: identifier})
        .order_by('-created_at').first()
    )
    payload = prev.payload if prev else {}
    verification = TelegramVerificationCode.issue(identifier, purpose, payload, channel=channel)
    try:
        sent = send_verification(verification)
    except Exception:
        logger.exception("Kodni qayta yuborib bo'lmadi (%s): %s", channel, identifier)
        sent = False
    if sent:
        request.session[LAST_SENT] = timezone.now().timestamp()
        messages.info(request, _("Yangi kod yuborildi."))
    else:
        messages.error(request, _("Kodni yuborishda xatolik yuz berdi."))
    return redirect('accounts:verify')


# --------------------------------------------------------------------------- #
#  Parolni tiklash
# --------------------------------------------------------------------------- #
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect(request.user.role_home_url)

    form = ForgotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        channel = cd.get('channel') or 'telegram'
        identifier = cd.get('email') if channel == 'email' else cd.get('telegram_chat_id')
        # Faqat admin/direktor o'zini ro'yxatdan o'tkazgan kanal orqali tiklaydi
        if channel == 'email':
            user = User.objects.filter(
                email__iexact=identifier, role__in=('admin', 'director')
            ).first()
        else:
            user = User.objects.filter(
                telegram_chat_id=identifier, role__in=('admin', 'director')
            ).first()
        if user:
            verification = TelegramVerificationCode.issue(identifier, 'reset', channel=channel)
            try:
                sent = send_verification(verification)
            except Exception:
                logger.exception("Parolni tiklash kodini yuborib bo'lmadi (%s): %s", channel, identifier)
                sent = False
            if not sent:
                messages.error(request, _("Kodni yuborishda xatolik. Ma'lumotlaringizni tekshiring."))
                return render(request, 'accounts/forgot.html', {'form': form})
            request.session[PENDING_CHAT] = identifier
            request.session[PENDING_CHANNEL] = channel
            request.session[PENDING_PURPOSE] = 'reset'
            request.session[LAST_SENT] = timezone.now().timestamp()
        else:
            # Topilmasa ham bir xil javob (identifikatorni taxmin qilishdan himoya)
            request.session[PENDING_CHAT] = identifier
            request.session[PENDING_CHANNEL] = channel
            request.session[PENDING_PURPOSE] = 'reset'
        if channel == 'email':
            messages.info(request, _("Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi."))
        else:
            messages.info(request, _("Agar bu ID ro'yxatdan o'tgan bo'lsa, kod botingizga yuborildi."))
        return redirect('accounts:verify')

    return render(request, 'accounts/forgot.html', {'form': form})


def reset_password(request):
    identifier = request.session.get(RESET_OK)
    channel = request.session.get(RESET_CHANNEL, 'telegram')
    if not identifier:
        messages.warning(request, _("Avval kod bilan tasdiqlang."))
        return redirect('accounts:forgot_password')

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if channel == 'email':
            user = User.objects.filter(
                email__iexact=identifier, role__in=('admin', 'director')
            ).first()
        else:
            user = User.objects.filter(
                telegram_chat_id=identifier, role__in=('admin', 'director')
            ).first()
        if not user:
            messages.error(request, _("Foydalanuvchi topilmadi."))
            return redirect('accounts:login_page')
        user.set_password(form.cleaned_data['password1'])
        user.save(update_fields=['password'])
        request.session.pop(RESET_OK, None)
        request.session.pop(RESET_CHANNEL, None)
        messages.success(request, _("Parol yangilandi. Endi kirishingiz mumkin."))
        return redirect('accounts:login_page')

    return render(request, 'accounts/reset.html', {'form': form, 'identifier': identifier, 'channel': channel})


@login_required
def force_password(request):
    """Admin parolni reset qilgach yoki yangi parol talab qilinganda — majburiy yangilash modali."""
    if not request.user.must_change_password:
        return redirect(request.user.role_home_url)

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = request.user
        user.set_password(form.cleaned_data['password1'])
        user.must_change_password = False
        user.plain_password = ''  # ko'rinadigan parolni tozalaymiz (foydalanuvchi o'zgartirdi)
        user.save(update_fields=['password', 'must_change_password', 'plain_password'])
        # set_password sessiyani buzmasligi uchun qayta kiritamiz
        login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
        messages.success(request, _("Parol muvaffaqiyatli yangilandi."))
        return redirect(user.role_home_url)

    return render(request, 'accounts/force_password.html', {'form': form})


def reset_help(request):
    """O'qituvchi/o'quvchi uchun parolni tiklash yo'riqnomasi (Telegram bot)."""
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
    return render(request, 'accounts/reset_help.html', {'bot_username': bot_username})


# --------------------------------------------------------------------------- #
#  Admin: Telegram bot orqali kelgan parol tiklash murojaatlari
# --------------------------------------------------------------------------- #
@role_required('admin')
def reset_requests(request):
    qs = PasswordResetRequest.objects.select_related('matched_user', 'resolved_by')
    pending = qs.filter(status='pending')
    history = qs.exclude(status='pending')[:30]
    return render(request, 'accounts/reset_requests.html', {
        'pending': pending,
        'history': history,
        'pending_count': pending.count(),
    })


@role_required('admin')
@require_POST
def reset_request_resolve(request, pk):
    req = get_object_or_404(PasswordResetRequest, pk=pk)
    if req.status != 'pending':
        messages.info(request, _("Bu murojaat allaqachon ko'rib chiqilgan."))
        return redirect('accounts:reset_requests')

    action = request.POST.get('action', 'resolve')

    if action == 'reject':
        req.status = 'rejected'
        req.resolved_by = request.user
        req.resolved_at = timezone.now()
        req.note = request.POST.get('note', '')[:255]
        req.save(update_fields=['status', 'resolved_by', 'resolved_at', 'note'])
        messages.success(request, _("Murojaat rad etildi."))
        return redirect('accounts:reset_requests')

    # --- Yangi parol o'rnatish ---
    user = req.matched_user
    username_override = request.POST.get('username', '').strip()
    if username_override:
        u2 = User.objects.filter(username__iexact=username_override).first()
        if u2:
            user = u2
    if user is None:
        messages.error(
            request,
            _("Foydalanuvchi topilmadi. Login (username) ni qo'lda kiriting va qaytadan urinib ko'ring."),
        )
        return redirect('accounts:reset_requests')

    new_password = request.POST.get('new_password', '').strip()
    if len(new_password) < 6:
        messages.error(request, _("Parol kamida 6 ta belgidan iborat bo'lishi kerak."))
        return redirect('accounts:reset_requests')

    user.set_password(new_password)
    user.plain_password = new_password      # admin ko'rishi uchun
    user.must_change_password = False       # admin bergan ishlaydigan parol
    user.save(update_fields=['password', 'plain_password', 'must_change_password'])

    req.matched_user = user
    req.status = 'resolved'
    req.resolved_by = request.user
    req.resolved_at = timezone.now()
    req.save(update_fields=['matched_user', 'status', 'resolved_by', 'resolved_at'])

    # Botga yangi parolni yuboramiz
    sent = False
    try:
        from cabinet.telegram import notify_new_password
        sent = notify_new_password(
            req.telegram_chat_id, user.username, new_password,
            role_label=user.get_role_display(),
        )
    except Exception:
        logger.exception("Yangi parolni botga yuborishda xatolik")

    if sent:
        messages.success(request, _("Yangi parol o'rnatildi va %(username)s ga botga yuborildi.") % {'username': user.username})
    else:
        messages.warning(
            request,
            _("Parol o'rnatildi (%(username)s), lekin botga yuborilmadi "
              "(bot tokeni yoki chat ID yo'q). Parolni qo'lda yetkazing: %(password)s")
            % {'username': user.username, 'password': new_password},
        )
    return redirect('accounts:reset_requests')


# --------------------------------------------------------------------------- #
#  Admin: foydalanuvchilarni boshqarish (CRUD + parol + impersonatsiya)
# --------------------------------------------------------------------------- #
import secrets

from django.db.models import Q


@role_required('admin')
def user_list(request):
    role = request.GET.get('role', '')
    q = request.GET.get('q', '').strip()
    users = User.objects.all().order_by('role', 'username')
    if role:
        users = users.filter(role=role)
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
            | Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
        )
    role_tabs = [
        {'key': key, 'label': label, 'count': User.objects.filter(role=key).count()}
        for key, label in User.ROLE_CHOICES
    ]
    return render(request, 'accounts/users_list.html', {
        'users': users,
        'role': role,
        'q': q,
        'role_tabs': role_tabs,
        'total': User.objects.count(),
    })


@role_required('admin')
def user_create(request):
    form = AdminUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        password = (form.cleaned_data.get('password') or '').strip() or secrets.token_urlsafe(6)
        user.set_password(password)
        user.plain_password = password
        if user.role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif user.role in ('director', 'teacher'):
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        user.save()
        messages.success(
            request,
            _("Foydalanuvchi yaratildi — login: %(username)s, parol: %(password)s")
            % {'username': user.username, 'password': password},
        )
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'is_new': True})


@role_required('admin')
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = AdminUserForm(request.POST or None, instance=target)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        password = (form.cleaned_data.get('password') or '').strip()
        if password:
            user.set_password(password)
            user.plain_password = password
        if user.role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif user.role in ('director', 'teacher'):
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        user.save()
        messages.success(request, _("%(username)s ma'lumotlari saqlandi.") % {'username': user.username})
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {
        'form': form, 'is_new': False, 'target': target,
    })


@role_required('admin')
@require_POST
def user_set_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    password = (request.POST.get('password') or '').strip() or secrets.token_urlsafe(6)
    target.set_password(password)
    target.plain_password = password
    target.save(update_fields=['password', 'plain_password'])
    # O'qituvchi/o'quvchi bo'lsa va Telegram ulangan bo'lsa — botga yuboramiz
    sent = False
    chat_id = ''
    if target.role == 'student':
        chat_id = getattr(getattr(target, 'student_profile', None), 'telegram_chat_id', '') or ''
    if chat_id:
        try:
            from cabinet.telegram import notify_new_password
            sent = notify_new_password(chat_id, target.username, password, target.get_role_display())
        except Exception:
            logger.exception("Parolni botga yuborishda xatolik")
    suffix = _(" (botga yuborildi)") if sent else ""
    messages.success(request, _("%(username)s uchun yangi parol: %(password)s%(suffix)s")
                     % {'username': target.username, 'password': password, 'suffix': suffix})
    return redirect('accounts:user_list')


@role_required('admin')
@require_POST
def user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, _("O'zingizni o'chira olmaysiz."))
        return redirect('accounts:user_list')
    name = target.username
    target.delete()
    messages.success(request, _("%(name)s o'chirildi.") % {'name': name})
    return redirect('accounts:user_list')


@role_required('admin')
def impersonate(request, pk):
    """Admin boshqa foydalanuvchi hisobiga kiradi (uning sahifasini ko'rish uchun)."""
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        return redirect(request.user.role_home_url)
    admin_id = request.user.pk
    login(request, target, backend='accounts.backends.EmailOrUsernameBackend')
    request.session['impersonator_id'] = admin_id
    messages.info(request, _("Siz %(name)s hisobiga kirdingiz (admin sifatida).") % {'name': target.display_name})
    return redirect(target.role_home_url)


@login_required
def stop_impersonation(request):
    admin_id = request.session.pop('impersonator_id', None)
    if not admin_id:
        return redirect(request.user.role_home_url)
    admin = User.objects.filter(pk=admin_id).first()
    if admin is None:
        logout(request)
        return redirect('accounts:login_page')
    login(request, admin, backend='accounts.backends.EmailOrUsernameBackend')
    messages.success(request, _("Admin hisobingizga qaytdingiz."))
    return redirect('accounts:user_list')


# --------------------------------------------------------------------------- #
#  Sozlamalar (admin): o'z paroli, markaz ma'lumotlari, o'quvchi/o'qituvchi loginlari
# --------------------------------------------------------------------------- #
@role_required('admin')
def settings_home(request):
    from dashboard.models import CenterProfile

    center = CenterProfile.get_solo()
    context = {
        'password_form': ChangeOwnPasswordForm(user=request.user),
        'center_form': CenterProfileForm(instance=center),
        'center': center,
        'students': User.objects.filter(role='student').order_by('username'),
        'teachers': User.objects.filter(role='teacher').order_by('username'),
        'directors': User.objects.filter(role='director').order_by('username'),
        'admins': User.objects.filter(role='admin').order_by('username'),
        'active_tab': request.GET.get('tab', 'account'),
    }
    return render(request, 'accounts/settings.html', context)


@role_required('admin')
@require_POST
def settings_password(request):
    form = ChangeOwnPasswordForm(request.POST, user=request.user)
    if form.is_valid():
        user = request.user
        user.set_password(form.cleaned_data['new_password1'])
        user.plain_password = ''
        user.must_change_password = False
        user.save(update_fields=['password', 'plain_password', 'must_change_password'])
        login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
        messages.success(request, _("Parolingiz muvaffaqiyatli o'zgartirildi."))
        return redirect('accounts:settings_home')
    # Xatolarni ko'rsatish uchun to'liq sahifani qayta chizamiz
    from dashboard.models import CenterProfile
    center = CenterProfile.get_solo()
    context = {
        'password_form': form,
        'center_form': CenterProfileForm(instance=center),
        'center': center,
        'students': User.objects.filter(role='student').order_by('username'),
        'teachers': User.objects.filter(role='teacher').order_by('username'),
        'directors': User.objects.filter(role='director').order_by('username'),
        'admins': User.objects.filter(role='admin').order_by('username'),
        'active_tab': 'account',
    }
    return render(request, 'accounts/settings.html', context)


@role_required('admin')
@require_POST
def settings_center(request):
    from dashboard.models import CenterProfile

    center = CenterProfile.get_solo()
    form = CenterProfileForm(request.POST, request.FILES, instance=center)
    if form.is_valid():
        form.save()
        messages.success(request, _("Markaz ma'lumotlari saqlandi."))
        return redirect(reverse('accounts:settings_home') + '?tab=center')
    context = {
        'password_form': ChangeOwnPasswordForm(user=request.user),
        'center_form': form,
        'center': center,
        'students': User.objects.filter(role='student').order_by('username'),
        'teachers': User.objects.filter(role='teacher').order_by('username'),
        'directors': User.objects.filter(role='director').order_by('username'),
        'admins': User.objects.filter(role='admin').order_by('username'),
        'active_tab': 'center',
    }
    return render(request, 'accounts/settings.html', context)


# --------------------------------------------------------------------------- #
#  Profil va chiqish
# --------------------------------------------------------------------------- #
@login_required
def profile(request):
    # O'quvchilar kabinet ko'rinishida, xodimlar admin ko'rinishida ko'radi
    base_template = 'cabinet/base_cabinet.html' if request.user.role == 'student' else 'base.html'
    form = ProfileForm(instance=request.user)
    password_form = ChangeOwnPasswordForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'password':
            password_form = ChangeOwnPasswordForm(request.POST, user=request.user)
            if password_form.is_valid():
                user = request.user
                user.set_password(password_form.cleaned_data['new_password1'])
                user.plain_password = ''
                user.must_change_password = False
                user.save(update_fields=['password', 'plain_password', 'must_change_password'])
                # set_password sessiyani buzmasligi uchun qayta kiritamiz
                login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
                messages.success(request, _("Parolingiz muvaffaqiyatli o'zgartirildi."))
                return redirect('accounts:profile')
        else:
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, _("Profil ma'lumotlari saqlandi."))
                return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'form': form,
        'password_form': password_form,
        'base_template': base_template,
    })


@login_required
@require_POST
def upload_avatar(request):
    """Profil rasmini yuklash — har qanday foydalanuvchi (admin/teacher/student)
    o'z rasmini yuklaydi. Rasm header va sozlamalarda ko'rinadi."""
    f = request.FILES.get('avatar')
    if not f:
        messages.error(request, _("Rasm tanlanmadi."))
    elif f.size > 5 * 1024 * 1024:
        messages.error(request, _("Rasm hajmi 5 MB dan oshmasligi kerak."))
    elif not f.content_type.startswith('image/'):
        messages.error(request, _("Faqat rasm fayli yuklang."))
    else:
        request.user.avatar = f
        request.user.save(update_fields=['avatar'])
        messages.success(request, _("Profil rasmingiz yangilandi."))
    return redirect(request.POST.get('next') or 'accounts:settings_home')


def logout_view(request):
    logout(request)
    messages.info(request, _("Tizimdan chiqdingiz."))
    return redirect('accounts:login_page')
