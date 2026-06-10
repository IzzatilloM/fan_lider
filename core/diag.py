"""VAQTINCHALIK diagnostika endpoint — Render (PostgreSQL, DEBUG=False) muhitidagi
haqiqiy xatolik traceback'ini aniqlash uchun. Maxfiy token bilan himoyalangan.
Xato topilgach BU FAYL VA URL O'CHIRILADI.
"""
import traceback

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.messages import get_messages
from django.http import HttpResponse, HttpResponseNotFound
from django.test import Client

# Vaqtinchalik maxfiy token (diagnostika tugagach olib tashlanadi)
DIAG_TOKEN = "fl-diag-7yq2-2026"

PAGES = [
    ("/", "Bosh sahifa (admin home)"),
    ("/director/", "Direktor paneli"),
    ("/salaries/", "Oyliklar (AI) sahifasi"),
    ("/salaries/employees/", "Xodimlar"),
    ("/students/", "O'quvchilar"),
    ("/courses/", "Guruhlar"),
    ("/instructors/", "O'qituvchilar"),
    ("/payments/", "To'lovlar paneli"),
    ("/monitoring/", "Monitoring"),
    ("/accounts/settings/", "Sozlamalar"),
    ("/accounts/users/", "Foydalanuvchilar"),
]


def run_diag(request, token):
    if token != DIAG_TOKEN:
        return HttpResponseNotFound("not found")

    User = get_user_model()
    admin = (User.objects.filter(is_superuser=True).first()
             or User.objects.filter(role="admin").first())
    director = User.objects.filter(role="director").first()

    host = request.get_host()
    lines = []
    lines.append(f"HOST={host}  DEBUG={settings.DEBUG}  DB={settings.DATABASES['default']['ENGINE']}")
    lines.append(f"MAX_ADMINS={getattr(settings, 'MAX_ADMINS', '?')}  "
                 f"MAX_DIRECTORS={getattr(settings, 'MAX_DIRECTORS', '?')}")
    lines.append(f"admin={admin.username if admin else None}  "
                 f"director={director.username if director else None}")
    lines.append(f"counts: users={User.objects.count()}")
    lines.append("-" * 72)

    # --- Barcha foydalanuvchilar holati ---
    lines.append("FOYDALANUVCHILAR:")
    for u in User.objects.all().order_by('id'):
        lines.append(
            f"  id={u.id} user='{u.username}' role='{getattr(u,'role','')}' "
            f"active={u.is_active} super={u.is_superuser} staff={u.is_staff} "
            f"usable_pw={u.has_usable_password()} email='{u.email}'"
        )
    lines.append("-" * 72)

    # --- LOGIN sinovi: ?u=...&p=...&role=... (haqiqiy login_page oqimi) ---
    test_u = request.GET.get('u')
    test_p = request.GET.get('p')
    test_role = request.GET.get('role', 'admin')
    if test_u and test_p:
        lines.append(f"LOGIN SINOVI: u='{test_u}' role='{test_role}'")
        # 1) authenticate (backend darajasi)
        au = authenticate(request, username=test_u, password=test_p)
        lines.append(f"  authenticate() -> {'MUVAFFAQIYAT user=' + au.username if au else 'None (login yoki parol xato)'}")
        # 2) to'liq login_page POST oqimi (rol tekshiruvi + admin_login_allowed bilan)
        c = Client(raise_request_exception=True, enforce_csrf_checks=False)
        try:
            resp = c.post('/accounts/login/', {
                'identifier': test_u, 'password': test_p, 'role': test_role,
            }, secure=True, SERVER_NAME=host, follow=True)
            msgs = [f"{m.tags}:{m.message}" for m in get_messages(resp.wsgi_request)]
            chain = ' -> '.join(f"{u}({s})" for u, s in resp.redirect_chain) or '(redirect yo\'q)'
            lines.append(f"  login_page POST -> status={resp.status_code}  redir={chain}")
            lines.append(f"  xabarlar: {msgs}")
        except Exception:
            lines.append("  login_page POST -> XATOLIK:")
            lines.append(traceback.format_exc())
        lines.append("-" * 72)

    lines.append("=" * 72)

    def probe(user, label_user):
        for path, label in PAGES:
            c = Client(raise_request_exception=True)
            c.force_login(user)
            try:
                resp = c.get(path, secure=True, SERVER_NAME=host, follow=True)
                lines.append(f"[{label_user}] {resp.status_code:>3}  {path}  ({label})")
            except Exception:
                lines.append(f"[{label_user}] !!! XATOLIK  {path}  ({label})")
                lines.append("-" * 72)
                lines.append(traceback.format_exc())
                lines.append("-" * 72)

    if admin:
        probe(admin, "admin")
    lines.append("=" * 72)
    if director:
        # Direktor uchun faqat asosiy sahifalar
        for path, label in [("/", "home->director"), ("/director/", "Direktor paneli")]:
            c = Client(raise_request_exception=True)
            c.force_login(director)
            try:
                resp = c.get(path, secure=True, SERVER_NAME=host, follow=True)
                lines.append(f"[director] {resp.status_code:>3}  {path}  ({label})")
            except Exception:
                lines.append(f"[director] !!! XATOLIK  {path}  ({label})")
                lines.append("-" * 72)
                lines.append(traceback.format_exc())
                lines.append("-" * 72)

    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
