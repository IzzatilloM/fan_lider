"""Oylik hisoblash dvigateli (formula + KPI).

Suniy intellekt (Claude) bo'lmaganida ham aniq, izohlanadigan hisob-kitob beradi.
Barcha summalar Decimal va so'mda.
"""
from decimal import ROUND_HALF_UP, Decimal

Q = Decimal('0.01')


def _d(value):
    return Decimal(str(value or 0))


def _money(value):
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def compute_kpi_score(attendance_rate, avg_score, late_count, absence_count):
    """0..100 oralig'idagi KPI ko'rsatkichi.

    60% davomat + 40% o'zlashtirish, kechikish/sababsiz kelmaslik uchun jarima.
    """
    attendance = _d(attendance_rate)
    score = _d(avg_score)
    base = attendance * Decimal('0.6') + score * Decimal('0.4')
    penalty = _d(late_count) * Decimal('2') + _d(absence_count) * Decimal('5')
    kpi = base - penalty
    if kpi < 0:
        kpi = Decimal('0')
    if kpi > 100:
        kpi = Decimal('100')
    return kpi.quantize(Q, rounding=ROUND_HALF_UP)


def compute(employee, metrics):
    """Xodim va metrikalar asosida oylikni hisoblaydi.

    `metrics` — dict yoki shu maydonlarga ega obyekt:
        worked_hours, students_count, attendance_rate, avg_score,
        late_count, absence_count, manual_bonus, manual_penalty
    """
    def g(key, default=0):
        if isinstance(metrics, dict):
            return metrics.get(key, default)
        return getattr(metrics, key, default)

    etype = employee.employment_type
    base_salary = _d(employee.base_salary)
    hourly_rate = _d(employee.hourly_rate)
    per_student_rate = _d(employee.per_student_rate)

    worked_hours = _d(g('worked_hours'))
    students_count = _d(g('students_count'))

    # --- Asosiy tarkib ---
    base_amount = Decimal('0')
    hours_amount = Decimal('0')
    students_amount = Decimal('0')

    if etype in ('fixed', 'mixed'):
        base_amount = base_salary
    if etype in ('hourly', 'mixed'):
        hours_amount = hourly_rate * worked_hours
    if etype in ('per_student', 'mixed'):
        students_amount = per_student_rate * students_count

    # --- KPI bonusi ---
    kpi_score = compute_kpi_score(
        g('attendance_rate'), g('avg_score'), g('late_count'), g('absence_count')
    )
    # Bonus bazasi: belgilangan oylik bo'lsa o'shandan, aks holda asosiy tushum
    bonus_base = base_salary if base_salary > 0 else (hours_amount + students_amount)
    kpi_pct = _d(employee.kpi_bonus_pct) / Decimal('100')
    kpi_bonus = bonus_base * kpi_pct * (kpi_score / Decimal('100'))

    # --- Jarimalar ---
    late_penalty = _d(employee.late_penalty) * _d(g('late_count'))
    manual_penalty = _d(g('manual_penalty'))
    penalties_amount = late_penalty + manual_penalty

    manual_bonus = _d(g('manual_bonus'))

    gross_amount = base_amount + hours_amount + students_amount + kpi_bonus + manual_bonus
    total_amount = gross_amount - penalties_amount
    if total_amount < 0:
        total_amount = Decimal('0')

    breakdown = {
        'lines': [
            {'label': "Belgilangan oylik", 'amount': float(_money(base_amount))},
            {'label': "Soatbay (soat × stavka)", 'amount': float(_money(hours_amount))},
            {'label': "O'quvchilar bo'yicha", 'amount': float(_money(students_amount))},
            {'label': f"KPI bonusi ({kpi_score}%)", 'amount': float(_money(kpi_bonus))},
            {'label': "Qo'shimcha bonus", 'amount': float(_money(manual_bonus))},
            {'label': "Kechikish jarimasi", 'amount': -float(_money(late_penalty))},
            {'label': "Qo'shimcha jarima", 'amount': -float(_money(manual_penalty))},
        ],
        'kpi_score': float(kpi_score),
    }

    return {
        'base_amount': _money(base_amount),
        'hours_amount': _money(hours_amount),
        'students_amount': _money(students_amount),
        'kpi_bonus': _money(kpi_bonus),
        'penalties_amount': _money(penalties_amount),
        'gross_amount': _money(gross_amount),
        'total_amount': _money(total_amount),
        'kpi_score': kpi_score,
        'breakdown': breakdown,
    }
