"""Rolga asoslangan ruxsat dekoratorlari."""
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.translation import gettext as _


def role_required(*roles):
    """Faqat ko'rsatilgan rollarga ruxsat beradi."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login_page')
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied(_("Sizda bu sahifaga ruxsat yo'q."))
        return _wrapped
    return decorator


def staff_required(view_func):
    """Admin, menejer yoki o'qituvchi uchun."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login_page')
        if request.user.is_superuser or request.user.is_staff_role:
            return view_func(request, *args, **kwargs)
        messages.warning(request, _("Bu bo'limga faqat xodimlar kira oladi."))
        raise PermissionDenied(_("Ruxsat yo'q."))
    return _wrapped


def manager_required(view_func):
    """Admin yoki direktor uchun (to'lov, ro'yxat, monitoring boshqaruvi)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login_page')
        if request.user.is_superuser or request.user.role in ('admin', 'director'):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied(_("Bu amal faqat administrator/direktor uchun."))
    return _wrapped
