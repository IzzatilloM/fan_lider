"""Oyliklar (AI) — ko'rinishlar."""
import json
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required

from . import ai as ai_module
from .engine import compute
from .forms import EmployeeForm, MetricsForm
from .metrics import auto_metrics
from .models import Employee, SalaryPeriod, SalaryRecord, month_name


# --------------------------------------------------------------------------- #
#  Yordamchilar
# --------------------------------------------------------------------------- #
def _selected_period(request):
    now = timezone.now()
    try:
        year = int(request.GET.get('year') or request.POST.get('year') or now.year)
        month = int(request.GET.get('month') or request.POST.get('month') or now.month)
    except (TypeError, ValueError):
        year, month = now.year, now.month
    month = min(max(month, 1), 12)
    return year, month


def _recompute(record):
    result = compute(record.employee, record)
    record.apply_breakdown(result)
    record.computed_at = timezone.now()
    record.save()
    return record


# --------------------------------------------------------------------------- #
#  Bosh sahifa — davr bo'yicha oyliklar
# --------------------------------------------------------------------------- #
@staff_required
def home(request):
    year, month = _selected_period(request)
    period = SalaryPeriod.objects.filter(year=year, month=month).first()

    employees = Employee.objects.filter(is_active=True)
    records = {}
    if period:
        records = {r.employee_id: r for r in period.records.select_related('employee')}

    rows = [{'employee': e, 'record': records.get(e.id)} for e in employees]

    computed = [r for r in records.values()]
    total_payout = sum((r.total_amount for r in computed), Decimal('0'))
    ai_count = sum(1 for r in computed if r.ai_generated)
    avg_kpi = round(sum(float(r.kpi_score) for r in computed) / len(computed), 1) if computed else 0

    # --- Grafik ma'lumotlari ---
    pay_rows = sorted(computed, key=lambda r: float(r.total_amount), reverse=True)
    payout_series = [
        {'name': r.employee.full_name, 'total': float(r.total_amount), 'kpi': float(r.kpi_score)}
        for r in pay_rows if float(r.total_amount) > 0
    ]
    rating_dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for r in computed:
        g = (r.ai_rating or '').strip().upper()[:1]
        if g in rating_dist:
            rating_dist[g] += 1

    context = {
        'year': year, 'month': month, 'month_label': month_name(month),
        'period': period, 'rows': rows,
        'employees_count': employees.count(),
        'computed_count': len(computed),
        'ai_count': ai_count,
        'total_payout': total_payout,
        'avg_kpi': avg_kpi,
        'payout_json': json.dumps(payout_series),
        'rating_json': json.dumps(rating_dist),
        'years': list(range(timezone.now().year - 3, timezone.now().year + 1)),
        'months': [(i, month_name(i)) for i in range(1, 13)],
        'has_anthropic': bool(getattr(settings, 'GEMINI_API_KEY', '') or getattr(settings, 'ANTHROPIC_API_KEY', '')),
    }
    return render(request, 'salaries/home.html', context)


def _home_url(year, month):
    return f"{reverse('salaries:home')}?year={year}&month={month}"


# --------------------------------------------------------------------------- #
#  Davrni hisoblash (barcha xodimlar)
# --------------------------------------------------------------------------- #
def _is_ajax(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.GET.get('format') == 'json'
        or request.POST.get('format') == 'json'
    )


@manager_required
def compute_period(request):
    if request.method != 'POST':
        return redirect('salaries:home')
    year, month = _selected_period(request)
    period, _created = SalaryPeriod.objects.get_or_create(
        year=year, month=month, defaults={'created_by': request.user}
    )

    created, updated = 0, 0
    records = []
    for employee in Employee.objects.filter(is_active=True):
        record, is_new = SalaryRecord.objects.get_or_create(
            period=period, employee=employee
        )
        if is_new:
            # Yangi yozuv — metrikalarni avtomatik to'ldiramiz
            data = auto_metrics(employee, year, month)
            for key, value in data.items():
                setattr(record, key, value)
            created += 1
        else:
            updated += 1
        _recompute(record)
        records.append(record)

    # --- AJAX so'rovi: natijani modal uchun JSON qaytaramiz ---
    if _is_ajax(request):
        rows = []
        total = Decimal('0')
        for r in sorted(records, key=lambda x: float(x.total_amount), reverse=True):
            total += r.total_amount
            rows.append({
                'pk': r.pk,
                'name': r.employee.full_name,
                'initials': r.employee.initials,
                'position': r.employee.get_position_display(),
                'kpi': round(float(r.kpi_score)),
                'base': float(r.base_amount),
                'hours': float(r.hours_amount),
                'students': float(r.students_amount),
                'kpi_bonus': float(r.kpi_bonus),
                'penalties': float(r.penalties_amount),
                'total': float(r.total_amount),
                'status': r.get_status_display(),
                'status_badge': r.status_badge,
                'detail_url': reverse('salaries:record_detail', args=[r.pk]),
            })
        return JsonResponse({
            'ok': True,
            'period': f"{month_name(month)} {year}",
            'year': year,
            'month': month,
            'created': created,
            'updated': updated,
            'count': len(rows),
            'total': float(total),
            'rows': rows,
        })

    messages.success(
        request,
        _("%(period)s: %(created)s ta yangi hisoblandi, %(updated)s ta yangilandi.")
        % {'period': f"{month_name(month)} {year}", 'created': created, 'updated': updated},
    )
    return redirect(_home_url(year, month))


# --------------------------------------------------------------------------- #
#  AI tahlil — bitta yoki barcha yozuvlar
# --------------------------------------------------------------------------- #
@manager_required
def record_ai(request, pk):
    record = get_object_or_404(SalaryRecord.objects.select_related('employee'), pk=pk)
    result = ai_module.analyze(record.employee, record)
    if result['ai']:
        messages.success(request, _("AI tahlili tayyor."))
    else:
        messages.info(request, _("AI tahlili tuzildi (API kalitsiz, mahalliy rejim)."))
    return redirect('salaries:record_detail', pk=record.pk)


@manager_required
def period_ai_all(request):
    if request.method != 'POST':
        return redirect('salaries:home')
    year, month = _selected_period(request)
    period = SalaryPeriod.objects.filter(year=year, month=month).first()
    if not period:
        messages.warning(request, _("Avval oylikni hisoblang."))
        return redirect(_home_url(year, month))

    n_ai, n_local = 0, 0
    for record in period.records.select_related('employee'):
        result = ai_module.analyze(record.employee, record)
        if result['ai']:
            n_ai += 1
        else:
            n_local += 1

    if n_ai:
        messages.success(request, _("%(n)s ta xodim Claude AI bilan tahlil qilindi.") % {'n': n_ai})
    else:
        messages.info(
            request,
            _("%(n)s ta xodim mahalliy (offline) rejimda tahlil qilindi. "
              "AI uchun .env dagi GEMINI_API_KEY ni tekshiring va serverni qayta ishga tushiring.")
            % {'n': n_local},
        )
    return redirect(_home_url(year, month))


# --------------------------------------------------------------------------- #
#  Bitta yozuv
# --------------------------------------------------------------------------- #
@staff_required
def record_detail(request, pk):
    record = get_object_or_404(
        SalaryRecord.objects.select_related('employee', 'period'), pk=pk
    )
    return render(request, 'salaries/record_detail.html', {'record': record})


@manager_required
def record_metrics(request, pk):
    record = get_object_or_404(SalaryRecord.objects.select_related('employee', 'period'), pk=pk)
    form = MetricsForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        form.save()
        _recompute(record)
        messages.success(request, _("Metrikalar saqlandi va oylik qayta hisoblandi."))
        return redirect('salaries:record_detail', pk=record.pk)
    return render(request, 'salaries/record_metrics.html', {'form': form, 'record': record})


@manager_required
def record_refresh_auto(request, pk):
    record = get_object_or_404(SalaryRecord.objects.select_related('employee', 'period'), pk=pk)
    data = auto_metrics(record.employee, record.period.year, record.period.month)
    for key, value in data.items():
        setattr(record, key, value)
    _recompute(record)
    messages.success(request, _("Metrikalar monitoring ma'lumotlaridan yangilandi."))
    return redirect('salaries:record_detail', pk=record.pk)


@manager_required
def record_set_status(request, pk):
    record = get_object_or_404(SalaryRecord, pk=pk)
    status = request.POST.get('status')
    if status in dict(SalaryRecord.STATUS_CHOICES):
        record.status = status
        record.save(update_fields=['status', 'updated_at'])
        messages.success(request, _("Holat yangilandi: %(status)s.") % {'status': record.get_status_display()})
    return redirect('salaries:record_detail', pk=record.pk)


@staff_required
def payslip(request, pk):
    record = get_object_or_404(
        SalaryRecord.objects.select_related('employee', 'period'), pk=pk
    )
    return render(request, 'salaries/payslip.html', {'record': record})


# --------------------------------------------------------------------------- #
#  Xodimlar boshqaruvi
# --------------------------------------------------------------------------- #
@staff_required
def employee_list(request):
    employees = Employee.objects.all().select_related('user')
    return render(request, 'salaries/employee_list.html', {
        'employees': employees,
        'active_count': employees.filter(is_active=True).count(),
    })


@manager_required
def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Xodim qo'shildi."))
        return redirect('salaries:employees')
    return render(request, 'salaries/employee_form.html', {'form': form, 'is_new': True})


@manager_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Xodim ma'lumotlari yangilandi."))
        return redirect('salaries:employees')
    return render(request, 'salaries/employee_form.html', {'form': form, 'employee': employee})


@manager_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, _("Xodim o'chirildi."))
        return redirect('salaries:employees')
    return render(request, 'salaries/employee_confirm_delete.html', {'employee': employee})


@manager_required
def sync_employees(request):
    """Tizim foydalanuvchilaridan (admin/menejer/o'qituvchi) xodim profillarini yaratadi."""
    if request.method != 'POST':
        return redirect('salaries:employees')
    from django.contrib.auth import get_user_model
    User = get_user_model()

    pos_map = {'admin': 'admin', 'manager': 'manager', 'teacher': 'teacher'}
    created = 0
    for user in User.objects.filter(role__in=pos_map.keys()):
        if hasattr(user, 'employee_profile'):
            continue
        Employee.objects.create(
            user=user,
            full_name=user.display_name,
            position=pos_map.get(user.role, 'other'),
            employment_type='mixed',
        )
        created += 1
    if created:
        messages.success(request, _("%(n)s ta xodim foydalanuvchilardan qo'shildi.") % {'n': created})
    else:
        messages.info(request, _("Yangi xodim topilmadi — barchasi allaqachon mavjud."))
    return redirect('salaries:employees')
