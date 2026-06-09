from datetime import date as date_cls

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.decorators import staff_required
from courses.models import Course
from students.models import Student

from .forms import AssessmentForm, LessonForm
from .models import Assessment, Attendance, Lesson


def _is_manager(user):
    """Admin yoki direktor — barcha guruhlarni ko'radi."""
    return user.is_superuser or user.role in ('admin', 'director')


def _teacher_instructor(user):
    return getattr(user, 'instructor_profile', None) if user.role == 'teacher' else None


def _ensure_course_access(user, course):
    """O'qituvchi faqat o'z guruhiga kira oladi; admin/direktor — hammasiga."""
    if _is_manager(user):
        return
    inst = _teacher_instructor(user)
    if inst is not None and course.teacher_id == inst.id:
        return
    raise PermissionDenied("Bu guruh sizga biriktirilmagan.")


def _accessible_courses(user, qs=None):
    """Foydalanuvchi ko'ra oladigan guruhlar to'plami."""
    qs = qs if qs is not None else Course.objects.all()
    if _is_manager(user):
        return qs
    inst = _teacher_instructor(user)
    if inst is not None:
        return qs.filter(teacher_id=inst.id)
    return qs.none()


@staff_required
def monitoring_home(request):
    """Monitoring boshlang'ich sahifasi — guruhni tanlash."""
    courses = _accessible_courses(
        request.user, Course.objects.exclude(status='finished')
    ).select_related('subject', 'teacher__user').annotate(
        students=Count('enrollments', filter=Q(enrollments__status='active'))
    )
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    recent = Attendance.objects.filter(date__gte=week_ago)
    context = {
        'courses': courses,
        'attendance_week': recent.count(),
        'present_week': recent.filter(status__in=['present', 'late']).count(),
        'assessments_week': Assessment.objects.filter(date__gte=week_ago).count(),
        'lessons_week': Lesson.objects.filter(date__gte=week_ago).count(),
    }
    return render(request, 'monitoring/home.html', context)


@staff_required
def attendance_take(request, slug):
    """Guruh uchun davomat olish (tanlangan sanaga)."""
    course = get_object_or_404(Course, slug=slug)
    _ensure_course_access(request.user, course)
    date_str = request.GET.get('date') or request.POST.get('date')
    try:
        day = date_cls.fromisoformat(date_str) if date_str else timezone.now().date()
    except ValueError:
        day = timezone.now().date()

    enrollments = course.enrollments.filter(status='active').select_related('student')
    students = [en.student for en in enrollments]
    existing = {a.student_id: a for a in Attendance.objects.filter(course=course, date=day)}

    if request.method == 'POST':
        saved = 0
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if not status:
                continue
            Attendance.objects.update_or_create(
                student=student, course=course, date=day,
                defaults={'status': status, 'recorded_by': request.user},
            )
            saved += 1
        messages.success(request, _("%(n)s ta o'quvchi davomati saqlandi (%(day)s).")
                         % {'n': saved, 'day': day})
        return redirect(f"{request.path}?date={day.isoformat()}")

    rows = [
        {'student': s, 'current': existing[s.id].status if s.id in existing else ''}
        for s in students
    ]
    context = {
        'course': course, 'day': day, 'rows': rows,
        'status_choices': Attendance.STATUS_CHOICES,
    }
    return render(request, 'monitoring/attendance_take.html', context)


@staff_required
def attendance_journal(request, slug):
    """Guruh davomati jurnali (oy bo'yicha matritsa)."""
    course = get_object_or_404(Course, slug=slug)
    _ensure_course_access(request.user, course)
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    records = Attendance.objects.filter(course=course, date__year=year, date__month=month)
    days = sorted({a.date.day for a in records})
    lookup = {(a.student_id, a.date.day): a.status for a in records}

    enrollments = course.enrollments.filter(status='active').select_related('student')
    matrix = []
    for en in enrollments:
        student = en.student
        cells = [{'day': d, 'status': lookup.get((student.id, d), '')} for d in days]
        present = sum(1 for c in cells if c['status'] in ('present', 'late'))
        total = sum(1 for c in cells if c['status'])
        matrix.append({
            'student': student, 'cells': cells,
            'percent': round(present / total * 100) if total else 0,
        })
    context = {
        'course': course, 'year': year, 'month': month, 'days': days, 'matrix': matrix,
        'months': list(enumerate(
            [_("Yanvar"), _("Fevral"), _("Mart"), _("Aprel"), _("May"), _("Iyun"), _("Iyul"),
             _("Avgust"), _("Sentabr"), _("Oktabr"), _("Noyabr"), _("Dekabr")], start=1)),
    }
    return render(request, 'monitoring/attendance_journal.html', context)


@staff_required
def grade_book(request, slug):
    """Guruh baholar jurnali."""
    course = get_object_or_404(Course, slug=slug)
    _ensure_course_access(request.user, course)
    assessments = course.assessments.select_related('student').order_by('-date')[:200]

    enrollments = course.enrollments.filter(status='active').select_related('student')
    summary = []
    for en in enrollments:
        student = en.student
        avg = student.assessments.filter(course=course).aggregate(a=Avg('percentage'))['a']
        summary.append({'student': student, 'avg': round(avg, 1) if avg else 0})
    summary.sort(key=lambda x: x['avg'], reverse=True)

    return render(request, 'monitoring/grade_book.html', {
        'course': course, 'assessments': assessments, 'summary': summary,
    })


@staff_required
def assessment_create(request):
    initial = {}
    if request.GET.get('course'):
        initial['course'] = request.GET['course']
    if request.GET.get('student'):
        initial['student'] = request.GET['student']
    form = AssessmentForm(request.POST or None, initial=initial)
    if form.is_valid():
        assessment = form.save(commit=False)
        _ensure_course_access(request.user, assessment.course)
        assessment.recorded_by = request.user
        assessment.save()
        messages.success(request, _("Baho qo'shildi."))
        return redirect('monitoring:grade_book', slug=assessment.course.slug)
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yangi baho")})


@staff_required
def assessment_delete(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    _ensure_course_access(request.user, assessment.course)
    slug = assessment.course.slug
    if request.method == 'POST':
        assessment.delete()
        messages.success(request, _("Baho o'chirildi."))
        return redirect('monitoring:grade_book', slug=slug)
    return render(request, 'shared/confirm_delete.html', {'object': assessment, 'type': _('Baho')})


@staff_required
def lesson_journal(request, slug):
    course = get_object_or_404(Course, slug=slug)
    _ensure_course_access(request.user, course)
    lessons = course.lessons.all()
    form = LessonForm(request.POST or None, initial={'course': course.id})
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Dars qo'shildi."))
        return redirect('monitoring:lesson_journal', slug=slug)
    return render(request, 'monitoring/lesson_journal.html', {
        'course': course, 'lessons': lessons, 'form': form,
    })


@staff_required
def student_report(request, slug):
    """O'quvchining to'liq o'quv hisoboti."""
    student = get_object_or_404(Student, slug=slug)
    # O'qituvchi faqat o'z guruhidagi o'quvchini ko'radi
    if not _is_manager(request.user):
        inst = _teacher_instructor(request.user)
        in_my_group = inst is not None and student.enrollments.filter(
            course__teacher_id=inst.id
        ).exists()
        if not in_my_group:
            raise PermissionDenied("Bu o'quvchi sizning guruhingizda emas.")
    attendances = student.attendances.select_related('course').order_by('-date')[:50]
    assessments = student.assessments.select_related('course').order_by('-date')[:50]
    att_total = student.attendances.count()
    att_present = student.attendances.filter(status__in=['present', 'late']).count()
    by_course = []
    for en in student.enrollments.filter(status='active').select_related('course'):
        c = en.course
        avg = student.assessments.filter(course=c).aggregate(a=Avg('percentage'))['a']
        c_att = student.attendances.filter(course=c)
        c_total = c_att.count()
        c_present = c_att.filter(status__in=['present', 'late']).count()
        by_course.append({
            'course': c,
            'avg': round(avg, 1) if avg else 0,
            'attendance': round(c_present / c_total * 100) if c_total else 0,
        })
    context = {
        'student': student,
        'attendances': attendances,
        'assessments': assessments,
        'attendance_percent': round(att_present / att_total * 100) if att_total else 0,
        'by_course': by_course,
    }
    return render(request, 'monitoring/student_report.html', context)
