import json
from datetime import time as dtime
from decimal import Decimal

from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# Guruh "dars kunlari" -> Python hafta kunlari to'plami (Dushanba=0 ... Yakshanba=6)
WEEKDAY_SETS = {
    'mon_wed_fri': {0, 2, 4},
    'tue_thu_sat': {1, 3, 5},
    'everyday': {0, 1, 2, 3, 4, 5, 6},
    'weekend': {5, 6},
}
WEEKDAY_LABELS = [
    _("Dushanba"), _("Seshanba"), _("Chorshanba"), _("Payshanba"),
    _("Juma"), _("Shanba"), _("Yakshanba"),
]
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from courses.models import Course
from enrollments.models import Enrollment, RegistrationApplication
from instructors.models import Instructor
from monitoring.models import Attendance
from payments.models import UZB_MONTHS, Invoice, Payment
from students.models import Student


@login_required
def home(request):
    # Rolga qarab to'g'ri panelga yo'naltirish
    u = request.user
    if not (u.is_superuser or u.is_staff_role):
        return redirect('cabinet:overview')
    if u.role == 'director':
        return redirect('dashboard:director')
    if u.role == 'teacher':
        return redirect('dashboard:teacher')

    today = timezone.now()

    students = Student.objects.all()
    active_students = students.filter(status='active').count()

    revenue_month = Payment.objects.filter(
        paid_at__year=today.year, paid_at__month=today.month
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

    debtors = students.filter(balance__lt=0)
    total_debt = abs(debtors.aggregate(s=Sum('balance'))['s'] or Decimal('0'))

    new_apps = RegistrationApplication.objects.filter(status='new').count()
    month_apps = RegistrationApplication.objects.filter(
        created_at__year=today.year, created_at__month=today.month
    ).count()

    # Daromad — oxirgi 6 oy
    revenue_series = []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + (today.month - i - 1) // 12
        amount = Payment.objects.filter(paid_at__year=y, paid_at__month=m).aggregate(
            s=Sum('amount'))['s'] or 0
        revenue_series.append({'label': str(UZB_MONTHS[m - 1])[:3], 'value': float(amount)})

    # Arizalar holati bo'yicha
    app_status = {row['status']: row['c'] for row in
                  RegistrationApplication.objects.values('status').annotate(c=Count('id'))}
    app_funnel = [
        {'label': str(label), 'value': app_status.get(key, 0)}
        for key, label in RegistrationApplication.STATUS_CHOICES
    ]

    # Davomat — bu hafta
    week_ago = today.date() - timezone.timedelta(days=7)
    week_att = Attendance.objects.filter(date__gte=week_ago)
    week_total = week_att.count()
    week_present = week_att.filter(status__in=['present', 'late']).count()
    attendance_rate = round(week_present / week_total * 100) if week_total else 0

    # Yo'nalishlar bo'yicha o'quvchilar
    subject_dist = list(
        Enrollment.objects.filter(status='active')
        .values('course__subject__name')
        .annotate(c=Count('id')).order_by('-c')[:6]
    )

    avg_score = Student.objects.aggregate(a=Avg('assessments__percentage'))['a'] or 0

    context = {
        'total_students': students.count(),
        'active_students': active_students,
        'total_groups': Course.objects.exclude(status='finished').count(),
        'total_teachers': Instructor.objects.filter(is_active=True).count(),
        'revenue_month': revenue_month,
        'total_debt': total_debt,
        'debtors_count': debtors.count(),
        'new_apps': new_apps,
        'month_apps': month_apps,
        'attendance_rate': attendance_rate,
        'avg_score': round(avg_score, 1),
        'unpaid_invoices': Invoice.objects.exclude(status__in=['paid', 'cancelled']).count(),

        'revenue_series_json': json.dumps(revenue_series),
        'app_funnel_json': json.dumps(app_funnel),
        'subject_dist_json': json.dumps(subject_dist),

        'recent_apps': RegistrationApplication.objects.select_related('subject')[:6],
        'recent_payments': Payment.objects.select_related('student')[:6],
        'top_debtors': debtors.order_by('balance')[:6],
        'recruiting_courses': Course.objects.filter(status='recruiting').select_related('subject')[:5],
    }
    return render(request, 'dashboard/home.html', context)


# --------------------------------------------------------------------------- #
#  Direktor paneli — to'lovlar, o'quv jarayoni va o'quvchilar monitoringi
# --------------------------------------------------------------------------- #
@login_required
def director(request):
    u = request.user
    if not (u.is_superuser or u.role in ('admin', 'director')):
        raise PermissionDenied("Bu panel faqat direktor uchun.")

    today = timezone.now()
    students = Student.objects.all()
    active_students = students.filter(status='active').count()

    revenue_month = Payment.objects.filter(
        paid_at__year=today.year, paid_at__month=today.month
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

    debtors = students.filter(balance__lt=0)
    total_debt = abs(debtors.aggregate(s=Sum('balance'))['s'] or Decimal('0'))

    # Daromad — oxirgi 6 oy
    revenue_series = []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + (today.month - i - 1) // 12
        amount = Payment.objects.filter(paid_at__year=y, paid_at__month=m).aggregate(
            s=Sum('amount'))['s'] or 0
        revenue_series.append({'label': str(UZB_MONTHS[m - 1])[:3], 'value': float(amount)})

    # Davomat — bu hafta
    week_ago = today.date() - timezone.timedelta(days=7)
    week_att = Attendance.objects.filter(date__gte=week_ago)
    week_total = week_att.count()
    week_present = week_att.filter(status__in=['present', 'late']).count()
    attendance_rate = round(week_present / week_total * 100) if week_total else 0

    avg_score = Student.objects.aggregate(a=Avg('assessments__percentage'))['a'] or 0

    # O'qituvchilar bo'yicha o'quv jarayoni
    teachers = list(
        Instructor.objects.filter(is_active=True).annotate(
            groups_n=Count('courses', distinct=True),
        ).order_by('-groups_n')[:8]
    )

    # Guruhlar bo'yicha to'ldirilganlik (o'quvchilar soni bilan)
    groups = list(
        Course.objects.exclude(status='finished')
        .select_related('subject', 'teacher')
        .annotate(students_n=Count('enrollments', filter=Q(enrollments__status='active')))
        .order_by('-students_n')[:8]
    )

    subject_dist = list(
        Enrollment.objects.filter(status='active')
        .values('course__subject__name')
        .annotate(c=Count('id')).order_by('-c')[:6]
    )

    # --- Qo'shimcha monitoring: arizalar, yig'ilish, o'zlashtirish ---
    new_apps = RegistrationApplication.objects.filter(status='new').count()
    month_apps = RegistrationApplication.objects.filter(
        created_at__year=today.year, created_at__month=today.month
    ).count()
    unpaid_invoices = Invoice.objects.exclude(status__in=['paid', 'cancelled']).count()

    # To'lov yig'ilish darajasi (yig'ilgan / (yig'ilgan + qarz))
    denom = float(revenue_month) + float(total_debt)
    collection_rate = round(float(revenue_month) / denom * 100) if denom else 0

    # Eng yuqori o'zlashtirgan o'quvchilar
    top_students = list(
        students.annotate(avg=Avg('assessments__percentage'))
        .filter(avg__gt=0).order_by('-avg')[:6]
    )

    # Arizalar voronkasi (holat bo'yicha)
    app_status = {row['status']: row['c'] for row in
                  RegistrationApplication.objects.values('status').annotate(c=Count('id'))}
    app_funnel = [
        {'label': str(label), 'value': app_status.get(key, 0)}
        for key, label in RegistrationApplication.STATUS_CHOICES
    ]

    context = {
        'total_students': students.count(),
        'active_students': active_students,
        'total_groups': Course.objects.exclude(status='finished').count(),
        'total_teachers': Instructor.objects.filter(is_active=True).count(),
        'revenue_month': revenue_month,
        'total_debt': total_debt,
        'debtors_count': debtors.count(),
        'attendance_rate': attendance_rate,
        'avg_score': round(avg_score, 1),
        'new_apps': new_apps,
        'month_apps': month_apps,
        'unpaid_invoices': unpaid_invoices,
        'collection_rate': collection_rate,
        'revenue_series_json': json.dumps(revenue_series),
        'subject_dist_json': json.dumps(subject_dist),
        'app_funnel_json': json.dumps(app_funnel),
        'teachers': teachers,
        'groups': groups,
        'top_students': top_students,
        'top_debtors': debtors.order_by('balance')[:8],
        'recent_payments': Payment.objects.select_related('student')[:8],
    }
    return render(request, 'dashboard/director.html', context)


# --------------------------------------------------------------------------- #
#  O'qituvchi paneli — guruhlar, jadval, oylik, davomat va baholar
# --------------------------------------------------------------------------- #
@login_required
def teacher(request, pk=None):
    u = request.user
    is_manager = u.is_superuser or u.role in ('admin', 'director')
    if not (is_manager or u.role == 'teacher'):
        raise PermissionDenied("Bu panel faqat o'qituvchi uchun.")

    # Admin/direktor istalgan o'qituvchi panelini ko'ra oladi (pk orqali)
    admin_preview = None
    if pk is not None:
        if not is_manager:
            raise PermissionDenied("Boshqa o'qituvchi panelini ko'rish huquqi yo'q.")
        instructor = get_object_or_404(Instructor.objects.select_related('user'), pk=pk)
        admin_preview = instructor
    else:
        instructor = getattr(u, 'instructor_profile', None)
        # Admin/direktorning o'z o'qituvchi profili yo'q — qaysi o'qituvchi
        # panelini ko'rishni tanlash uchun o'qituvchilar ro'yxatiga yo'naltiramiz.
        if instructor is None and is_manager:
            messages.info(request, _("O'qituvchi panelini ko'rish uchun ro'yxatdan o'qituvchini tanlang."))
            return redirect('instructors:list')
    courses = []
    if instructor is not None:
        courses = list(
            instructor.courses.exclude(status='finished')
            .select_related('subject')
            .annotate(students_n=Count('enrollments', filter=Q(enrollments__status='active')))
        )

    # Bu o'qituvchining guruhlaridagi davomat / baho statistikasi
    course_ids = [c.id for c in courses]
    today = timezone.now()
    week_ago = today.date() - timezone.timedelta(days=7)
    week_att = Attendance.objects.filter(course_id__in=course_ids, date__gte=week_ago)
    week_total = week_att.count()
    week_present = week_att.filter(status__in=['present', 'late']).count()
    attendance_rate = round(week_present / week_total * 100) if week_total else 0

    total_students = sum(getattr(c, 'students_n', 0) for c in courses)

    # --- Jadval: bugungi darslar va haftalik dars kunlari ---
    def _by_time(c):
        return c.start_time or dtime(23, 59)

    today_wd = today.weekday()
    today_lessons = sorted(
        (c for c in courses if today_wd in WEEKDAY_SETS.get(c.weekdays, set())),
        key=_by_time,
    )
    week_schedule = []
    for wd in range(7):
        day_courses = sorted(
            (c for c in courses if wd in WEEKDAY_SETS.get(c.weekdays, set())),
            key=_by_time,
        )
        if day_courses:
            week_schedule.append({
                'label': WEEKDAY_LABELS[wd],
                'is_today': wd == today_wd,
                'courses': day_courses,
            })

    # Oylik (mavjud bo'lsa) — preview'da o'qituvchining o'zinikidan olinadi
    salary = None
    salary_owner = instructor.user if (admin_preview and instructor) else u
    employee = getattr(salary_owner, 'employee_profile', None)
    if employee is not None:
        salary = employee.base_salary

    context = {
        'instructor': instructor,
        'courses': courses,
        'total_groups': len(courses),
        'total_students': total_students,
        'attendance_rate': attendance_rate,
        'salary': salary,
        'employee': employee,
        'admin_preview': admin_preview,
        'today_lessons': today_lessons,
        'today_label': WEEKDAY_LABELS[today_wd],
        'week_schedule': week_schedule,
    }
    return render(request, 'dashboard/teacher.html', context)


# --------------------------------------------------------------------------- #
#  O'qituvchi — guruh o'quvchilari ro'yxati (aloqa, davomat, o'zlashtirish)
# --------------------------------------------------------------------------- #
@login_required
def teacher_students(request, pk=None):
    """O'qituvchi o'z guruhlaridagi o'quvchilarni bitta sahifada ko'radi:
    aloqa ma'lumotlari (telefon, Telegram), davomat % va o'rtacha bahosi bilan.
    Admin/direktor istalgan o'qituvchi ro'yxatini pk orqali ko'ra oladi."""
    u = request.user
    is_manager = u.is_superuser or u.role in ('admin', 'director')
    if not (is_manager or u.role == 'teacher'):
        raise PermissionDenied("Bu sahifa faqat o'qituvchi uchun.")

    admin_preview = None
    if pk is not None:
        if not is_manager:
            raise PermissionDenied("Boshqa o'qituvchi ro'yxatini ko'rish huquqi yo'q.")
        instructor = get_object_or_404(Instructor.objects.select_related('user'), pk=pk)
        admin_preview = instructor
    else:
        instructor = getattr(u, 'instructor_profile', None)
        if instructor is None and is_manager:
            messages.info(request, _("O'quvchilar ro'yxatini ko'rish uchun o'qituvchini tanlang."))
            return redirect('instructors:list')

    groups = []
    total_students = 0
    if instructor is not None:
        teacher_courses = (
            instructor.courses.exclude(status='finished')
            .select_related('subject')
            .order_by('subject__name', 'name')
        )
        for c in teacher_courses:
            roster = [
                e.student for e in (
                    c.enrollments.filter(status='active')
                    .select_related('student')
                    .order_by('student__last_name', 'student__first_name')
                )
            ]
            total_students += len(roster)
            groups.append({'course': c, 'students': roster})

    context = {
        'instructor': instructor,
        'groups': groups,
        'total_groups': len(groups),
        'total_students': total_students,
        'admin_preview': admin_preview,
    }
    return render(request, 'dashboard/teacher_students.html', context)
