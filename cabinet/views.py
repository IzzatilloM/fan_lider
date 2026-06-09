"""O'quvchining shaxsiy kabineti + Telegram bot webhook.

Har bir o'quvchi FAQAT o'zining profili, to'lovlari, kurslari, baholari va
davomatini ko'radi (request.user.student_profile orqali scoped).
"""
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.decorators import staff_required
from students.models import Student

logger = logging.getLogger(__name__)


def _get_student(request):
    """Joriy foydalanuvchiga bog'langan o'quvchi profilini qaytaradi (yoki None)."""
    return getattr(request.user, 'student_profile', None)


@login_required
def overview(request):
    student = _get_student(request)
    if student is None:
        messages.warning(request, _("Sizning hisobingiz hali o'quvchi profiliga bog'lanmagan. Markaz ma'muriyatiga murojaat qiling."))
        return render(request, 'cabinet/not_linked.html')
    return render(request, 'cabinet/overview.html', _build_overview_context(student))


@login_required
@require_POST
def upload_photo(request):
    """O'quvchi o'z profil rasmini yuklaydi (Student.photo)."""
    student = _get_student(request)
    if student is None:
        return HttpResponseForbidden(_("O'quvchi profili topilmadi."))
    f = request.FILES.get('photo')
    if not f:
        messages.error(request, _("Rasm tanlanmadi."))
    elif f.size > 5 * 1024 * 1024:
        messages.error(request, _("Rasm hajmi 5 MB dan oshmasligi kerak."))
    elif not f.content_type.startswith('image/'):
        messages.error(request, _("Faqat rasm fayli yuklang."))
    else:
        student.photo = f
        student.save(update_fields=['photo'])
        messages.success(request, _("Profil rasmingiz yangilandi."))
    from django.shortcuts import redirect
    return redirect('cabinet:overview')


@staff_required
def admin_view(request, slug):
    """Admin/xodim — istalgan o'quvchining kabinetini ko'radi (faqat ko'rish)."""
    student = get_object_or_404(Student, slug=slug)
    context = _build_overview_context(student)
    context['admin_preview'] = True
    return render(request, 'cabinet/overview.html', context)


def _build_overview_context(student):
    enrollments = (
        student.enrollments.select_related('course__subject', 'course__teacher')
        .all()
    )
    active_enrollments = [e for e in enrollments if e.status == 'active']

    # To'lovlar
    invoices = student.invoices.select_related('course').all()
    payments = student.payments.select_related('invoice__course').order_by('-paid_at')[:8]
    total_paid = student.payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    # Baholar
    assessments = student.assessments.select_related('course__subject').order_by('-date')
    recent_assessments = assessments[:10]

    # --- Baho foiz statistikasi ---
    overall_avg = float(student.average_score)          # umumiy o'rtacha foiz
    attendance_pct = student.attendance_percentage

    # Fan/kurs bo'yicha o'rtacha foiz (chart uchun)
    per_course = (
        student.assessments
        .values('course__name', 'course__subject__name', 'course__subject__color')
        .annotate(avg=Avg('percentage'), n=Count('id'))
        .order_by('-avg')
    )
    course_labels = [c['course__subject__name'] or c['course__name'] or '—' for c in per_course]
    course_values = [round(float(c['avg'] or 0), 1) for c in per_course]
    course_colors = [c['course__subject__color'] or '#D4640F' for c in per_course]

    # Baho taqsimoti (5/4/3/2)
    dist = {5: 0, 4: 0, 3: 0, 2: 0}
    for a in assessments:
        dist[a.grade_5] = dist.get(a.grade_5, 0) + 1
    grade_dist = [dist[5], dist[4], dist[3], dist[2]]

    # --- Guruhdagi reyting (har faol kurs bo'yicha) ---
    from enrollments.models import Enrollment
    from monitoring.models import Assessment

    rankings = []
    for en in active_enrollments:
        course = en.course
        member_ids = list(
            Enrollment.objects.filter(course=course, status='active')
            .values_list('student_id', flat=True)
        )
        if not member_ids:
            continue
        scores = (
            Assessment.objects.filter(course=course, student_id__in=member_ids)
            .values('student_id').annotate(a=Avg('percentage'))
        )
        score_map = {s['student_id']: float(s['a'] or 0) for s in scores}
        ranked = sorted(member_ids, key=lambda sid: score_map.get(sid, 0), reverse=True)
        my_rank = ranked.index(student.id) + 1 if student.id in ranked else None
        rankings.append({
            'course': course,
            'rank': my_rank,
            'total': len(ranked),
            'avg': round(score_map.get(student.id, 0), 1),
            'is_top3': my_rank is not None and my_rank <= 3,
        })
    rankings.sort(key=lambda r: (r['rank'] or 999))

    # --- O'tkazib yuborilgan darslar (qizilda ko'rsatiladi) ---
    from django.utils import timezone
    from payments.models import UZB_MONTHS

    missed_lessons = list(
        student.attendances.filter(status='absent')
        .select_related('course__subject').order_by('-date')[:12]
    )
    missed_count = student.attendances.filter(status='absent').count()

    # --- Oylik to'lovlar grafigi (oxirgi 6 oy) ---
    today = timezone.now()
    pay_labels, pay_values = [], []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + (today.month - i - 1) // 12
        amt = (
            student.payments.filter(paid_at__year=y, paid_at__month=m)
            .aggregate(s=Sum('amount'))['s'] or 0
        )
        pay_labels.append(f"{str(UZB_MONTHS[m - 1])[:3]} {str(y)[2:]}")
        pay_values.append(float(amt))

    # To'lanishi kerak bo'lgan summa (qarz)
    total_debt = student.debt_amount

    # Umumiy baho darajasi (matn)
    if overall_avg >= 86:
        perf_label, perf_class = _("A'lo"), 'success'
    elif overall_avg >= 71:
        perf_label, perf_class = _("Yaxshi"), 'success'
    elif overall_avg >= 56:
        perf_label, perf_class = _("Qoniqarli"), 'warning'
    elif overall_avg > 0:
        perf_label, perf_class = _("Past"), 'danger'
    else:
        perf_label, perf_class = _("Baho yo'q"), 'muted'

    context = {
        'student': student,
        'enrollments': enrollments,
        'active_enrollments': active_enrollments,
        'invoices': invoices,
        'payments': payments,
        'total_paid': total_paid,
        'assessments_count': assessments.count(),
        'recent_assessments': recent_assessments,
        'overall_avg': overall_avg,
        'attendance_pct': attendance_pct,
        'perf_label': perf_label,
        'perf_class': perf_class,
        'course_labels': course_labels,
        'course_values': course_values,
        'course_colors': course_colors,
        'grade_dist': grade_dist,
        'rankings': rankings,
        'missed_lessons': missed_lessons,
        'missed_count': missed_count,
        'pay_labels': pay_labels,
        'pay_values': pay_values,
        'total_debt': total_debt,
    }
    return context


# --------------------------------------------------------------------------- #
#  Telegram bot webhook
# --------------------------------------------------------------------------- #
@csrf_exempt
@require_POST
def telegram_webhook(request):
    """Telegram update'larni qabul qiladi (PythonAnywhere webhook)."""
    secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
    if secret:
        header = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if header != secret:
            return HttpResponseForbidden('bad secret')
    try:
        update = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    from .bot import handle_update
    try:
        handle_update(update)
    except Exception:
        logger.exception("Telegram update qayta ishlashda xatolik")
    # Telegramga doim 200 qaytaramiz (qayta yubormasligi uchun)
    return JsonResponse({'ok': True})
