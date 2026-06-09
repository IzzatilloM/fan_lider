"""Mobil ilova (Flutter) uchun DRF API view'lari.

Auth: JWT (login + parol yoki email + parol). Platformadagi har bir o'qituvchi
va o'quvchi o'z login/paroli bilan kira oladi.

Student endpoint'lari — `cabinet.views._build_overview_context` mantig'ini
takrorlaydi. Teacher endpoint'lari — `dashboard.views.teacher` mantig'ini.
"""
from datetime import time as dtime
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from courses.models import Course
from enrollments.models import Enrollment
from instructors.models import Instructor
from monitoring.models import Assessment, Attendance
from payments.models import UZB_MONTHS, Invoice, Payment
from students.models import Student

from .serializers import (
    AssessmentSerializer,
    AttendanceSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    InstructorProfileSerializer,
    InstructorProfileUpdateSerializer,
    InvoiceSerializer,
    LessonSerializer,
    PaymentSerializer,
    StudentMiniSerializer,
    StudentProfileSerializer,
    StudentProfileUpdateSerializer,
    UserSerializer,
)


def _truthy(value):
    """Multipart/JSON dan kelgan rost qiymatni aniqlash ('1'/'true'/'yes')."""
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

# Guruh "dars kunlari" -> Python hafta kunlari (Dushanba=0 ... Yakshanba=6)
WEEKDAY_SETS = {
    'mon_wed_fri': {0, 2, 4},
    'tue_thu_sat': {1, 3, 5},
    'everyday': {0, 1, 2, 3, 4, 5, 6},
    'weekend': {5, 6},
}
WEEKDAY_LABELS = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba",
]


# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #
class LoginSerializer(TokenObtainPairSerializer):
    """username (yoki email) + parol -> access/refresh token + foydalanuvchi.

    `EmailOrUsernameBackend` orqali email bilan ham kirish mumkin.
    """

    username_field = 'username'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['name'] = user.display_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        request = self.context.get('request')
        data['user'] = UserSerializer(self.user, context={'request': request}).data
        return data


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Joriy foydalanuvchi + rolga mos profil (kirgandan keyin panel tanlash uchun)."""
    user = request.user
    data = UserSerializer(user, context={'request': request}).data
    student = getattr(user, 'student_profile', None)
    instructor = getattr(user, 'instructor_profile', None)
    data['student'] = (
        StudentProfileSerializer(student, context={'request': request}).data
        if student else None
    )
    data['instructor'] = (
        InstructorProfileSerializer(instructor, context={'request': request}).data
        if instructor else None
    )
    return Response(data)


# --------------------------------------------------------------------------- #
#  O'quvchi (student) endpoint'lari
# --------------------------------------------------------------------------- #
def _require_student(request):
    return getattr(request.user, 'student_profile', None)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_overview(request):
    """O'quvchi kabinetining bosh sahifasi — barcha statistika bir javobda."""
    student = _require_student(request)
    if student is None:
        return Response(
            {'detail': "Sizning hisobingiz o'quvchi profiliga bog'lanmagan."},
            status=status.HTTP_403_FORBIDDEN,
        )
    ctx = {'request': request}

    enrollments = list(
        student.enrollments.select_related('course__subject', 'course__teacher').all()
    )
    active_enrollments = [e for e in enrollments if e.status == 'active']

    total_paid = student.payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    payments = student.payments.select_related('invoice__course').order_by('-paid_at')[:8]

    assessments = student.assessments.select_related('course__subject').order_by('-date')
    overall_avg = float(student.average_score)
    attendance_pct = student.attendance_percentage

    # Fan bo'yicha o'rtacha (radar/bar chart uchun)
    per_course = (
        student.assessments
        .values('course__name', 'course__subject__name', 'course__subject__color')
        .annotate(avg=Avg('percentage'), n=Count('id'))
        .order_by('-avg')
    )
    subject_performance = [
        {
            'label': c['course__subject__name'] or c['course__name'] or '—',
            'value': round(float(c['avg'] or 0), 1),
            'color': c['course__subject__color'] or '#D4640F',
        }
        for c in per_course
    ]

    # Baho taqsimoti (5/4/3/2)
    dist = {5: 0, 4: 0, 3: 0, 2: 0}
    for a in assessments:
        dist[a.grade_5] = dist.get(a.grade_5, 0) + 1
    grade_dist = [dist[5], dist[4], dist[3], dist[2]]

    # Guruhdagi reyting
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
            'course_name': course.name,
            'subject_icon': course.subject.icon if course.subject_id else '📘',
            'rank': my_rank,
            'total': len(ranked),
            'avg': round(score_map.get(student.id, 0), 1),
            'is_top3': my_rank is not None and my_rank <= 3,
        })
    rankings.sort(key=lambda r: (r['rank'] or 999))

    # O'tkazib yuborilgan darslar
    missed_count = student.attendances.filter(status='absent').count()

    # Oylik to'lovlar grafigi (oxirgi 6 oy)
    today = timezone.now()
    payment_series = []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + (today.month - i - 1) // 12
        amt = (
            student.payments.filter(paid_at__year=y, paid_at__month=m)
            .aggregate(s=Sum('amount'))['s'] or 0
        )
        payment_series.append({
            'label': f"{str(UZB_MONTHS[m - 1])[:3]} {str(y)[2:]}",
            'value': float(amt),
        })

    if overall_avg >= 86:
        perf_label, perf_class = "A'lo", 'success'
    elif overall_avg >= 71:
        perf_label, perf_class = 'Yaxshi', 'success'
    elif overall_avg >= 56:
        perf_label, perf_class = 'Qoniqarli', 'warning'
    elif overall_avg > 0:
        perf_label, perf_class = 'Past', 'danger'
    else:
        perf_label, perf_class = "Baho yo'q", 'muted'

    return Response({
        'student': StudentProfileSerializer(student, context=ctx).data,
        'stats': {
            'overall_avg': round(overall_avg, 1),
            'attendance_pct': attendance_pct,
            'active_courses': len(active_enrollments),
            'total_enrollments': len(enrollments),
            'balance': float(student.balance),
            'total_debt': float(student.debt_amount),
            'total_paid': float(total_paid),
            'assessments_count': assessments.count(),
            'missed_count': missed_count,
            'perf_label': perf_label,
            'perf_class': perf_class,
        },
        'subject_performance': subject_performance,
        'grade_dist': grade_dist,
        'rankings': rankings,
        'payment_series': payment_series,
        'enrollments': EnrollmentSerializer(enrollments, many=True, context=ctx).data,
        'recent_assessments': AssessmentSerializer(assessments[:10], many=True, context=ctx).data,
        'recent_payments': PaymentSerializer(payments, many=True, context=ctx).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_grades(request):
    student = _require_student(request)
    if student is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    qs = student.assessments.select_related('course__subject').order_by('-date')
    return Response(AssessmentSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_attendance(request):
    student = _require_student(request)
    if student is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    qs = student.attendances.select_related('course__subject').order_by('-date')[:120]
    summary = {
        'present': student.attendances.filter(status='present').count(),
        'late': student.attendances.filter(status='late').count(),
        'excused': student.attendances.filter(status='excused').count(),
        'absent': student.attendances.filter(status='absent').count(),
        'percentage': student.attendance_percentage,
    }
    return Response({
        'summary': summary,
        'records': AttendanceSerializer(qs, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_payments(request):
    student = _require_student(request)
    if student is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    ctx = {'request': request}
    payments = student.payments.select_related('invoice__course').order_by('-paid_at')
    invoices = student.invoices.select_related('course').all()
    return Response({
        'balance': float(student.balance),
        'total_debt': float(student.debt_amount),
        'total_paid': float(student.payments.aggregate(s=Sum('amount'))['s'] or 0),
        'invoices': InvoiceSerializer(invoices, many=True, context=ctx).data,
        'payments': PaymentSerializer(payments, many=True, context=ctx).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_courses(request):
    student = _require_student(request)
    if student is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    qs = student.enrollments.select_related('course__subject', 'course__teacher').all()
    return Response(EnrollmentSerializer(qs, many=True, context={'request': request}).data)


@api_view(['PATCH', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def student_profile_update(request):
    """O'quvchi o'z profilini tahrirlaydi (rasm yuklash + shaxsiy ma'lumotlar).

    `multipart/form-data` (rasm bilan) yoki `application/json` qabul qiladi.
    `remove_photo=1` yuborilsa, joriy rasm o'chiriladi.
    """
    student = _require_student(request)
    if student is None:
        return Response(
            {'detail': "Sizning hisobingiz o'quvchi profiliga bog'lanmagan."},
            status=status.HTTP_403_FORBIDDEN,
        )
    ctx = {'request': request}
    serializer = StudentProfileUpdateSerializer(
        student, data=request.data, partial=True, context=ctx,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    if _truthy(request.data.get('remove_photo')) and student.photo:
        student.photo.delete(save=False)
        student.photo = None
        student.save(update_fields=['photo'])

    return Response(StudentProfileSerializer(student, context=ctx).data)


# --------------------------------------------------------------------------- #
#  O'qituvchi (teacher) endpoint'lari
# --------------------------------------------------------------------------- #
def _require_instructor(request):
    return getattr(request.user, 'instructor_profile', None)


def _instructor_courses(instructor):
    return list(
        instructor.courses.exclude(status='finished')
        .select_related('subject')
        .annotate(students_n=Count('enrollments', filter=Q(enrollments__status='active')))
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_overview(request):
    """O'qituvchi panelining bosh sahifasi."""
    instructor = _require_instructor(request)
    if instructor is None:
        return Response(
            {'detail': "Sizning hisobingiz o'qituvchi profiliga bog'lanmagan."},
            status=status.HTTP_403_FORBIDDEN,
        )
    ctx = {'request': request}
    courses = _instructor_courses(instructor)
    course_ids = [c.id for c in courses]

    today = timezone.now()
    week_ago = today.date() - timezone.timedelta(days=7)
    week_att = Attendance.objects.filter(course_id__in=course_ids, date__gte=week_ago)
    week_total = week_att.count()
    week_present = week_att.filter(status__in=['present', 'late']).count()
    attendance_rate = round(week_present / week_total * 100) if week_total else 0
    total_students = sum(getattr(c, 'students_n', 0) for c in courses)

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
                'courses': CourseSerializer(day_courses, many=True, context=ctx).data,
            })

    # Oylik (mavjud bo'lsa)
    salary = None
    employee = getattr(request.user, 'employee_profile', None)
    if employee is not None:
        salary = float(employee.base_salary)
    elif instructor.salary:
        salary = float(instructor.salary)

    return Response({
        'instructor': InstructorProfileSerializer(instructor, context=ctx).data,
        'stats': {
            'total_groups': len(courses),
            'total_students': total_students,
            'attendance_rate': attendance_rate,
            'salary': salary,
        },
        'today_label': WEEKDAY_LABELS[today_wd],
        'today_lessons': CourseSerializer(today_lessons, many=True, context=ctx).data,
        'week_schedule': week_schedule,
        'courses': CourseSerializer(courses, many=True, context=ctx).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_groups(request):
    instructor = _require_instructor(request)
    if instructor is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    courses = _instructor_courses(instructor)
    return Response(CourseSerializer(courses, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_group_students(request, course_id):
    """Bitta guruhdagi faol o'quvchilar + so'nggi darslar."""
    instructor = _require_instructor(request)
    if instructor is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    try:
        course = instructor.courses.select_related('subject').get(pk=course_id)
    except Course.DoesNotExist:
        return Response({'detail': 'Guruh topilmadi.'}, status=404)

    ctx = {'request': request}
    student_ids = list(
        course.enrollments.filter(status='active').values_list('student_id', flat=True)
    )
    students = Student.objects.filter(id__in=student_ids).order_by('last_name', 'first_name')
    lessons = course.lessons.order_by('-date')[:10]
    return Response({
        'course': CourseSerializer(course, context=ctx).data,
        'students': StudentMiniSerializer(students, many=True, context=ctx).data,
        'lessons': LessonSerializer(lessons, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_schedule(request):
    instructor = _require_instructor(request)
    if instructor is None:
        return Response({'detail': 'Profil topilmadi.'}, status=403)
    ctx = {'request': request}
    courses = _instructor_courses(instructor)

    def _by_time(c):
        return c.start_time or dtime(23, 59)

    today_wd = timezone.now().weekday()
    week = []
    for wd in range(7):
        day_courses = sorted(
            (c for c in courses if wd in WEEKDAY_SETS.get(c.weekdays, set())),
            key=_by_time,
        )
        week.append({
            'label': WEEKDAY_LABELS[wd],
            'is_today': wd == today_wd,
            'courses': CourseSerializer(day_courses, many=True, context=ctx).data,
        })
    return Response(week)


@api_view(['PATCH', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def teacher_profile_update(request):
    """O'qituvchi o'z profilini tahrirlaydi (rasm yuklash + ma'lumotlar).

    `remove_photo=1` yuborilsa, joriy rasm o'chiriladi.
    """
    instructor = _require_instructor(request)
    if instructor is None:
        return Response(
            {'detail': "Sizning hisobingiz o'qituvchi profiliga bog'lanmagan."},
            status=status.HTTP_403_FORBIDDEN,
        )
    ctx = {'request': request}
    serializer = InstructorProfileUpdateSerializer(
        instructor, data=request.data, partial=True, context=ctx,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    if _truthy(request.data.get('remove_photo')) and instructor.image:
        instructor.image.delete(save=False)
        instructor.image = None
        instructor.save(update_fields=['image'])

    return Response(InstructorProfileSerializer(instructor, context=ctx).data)
