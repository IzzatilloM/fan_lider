"""O'qituvchilar uchun oylik metrikalarini monitoring/kurslardan avtomatik yig'ish.

Bog'langan o'qituvchi profili bo'lmasa, bo'sh (0) metrikalar qaytadi —
admin keyin qo'lda to'ldiradi.
"""
from decimal import Decimal


def auto_metrics(employee, year, month):
    """Berilgan davr uchun metrikalar dict qaytaradi."""
    data = {
        'worked_days': 0,
        'worked_hours': Decimal('0'),
        'lessons_count': 0,
        'groups_count': 0,
        'students_count': 0,
        'attendance_rate': Decimal('0'),
        'avg_score': Decimal('0'),
        'late_count': 0,
        'absence_count': 0,
    }

    instructor = employee.instructor
    if instructor is None:
        return data

    from courses.models import Course
    from monitoring.models import Assessment, Attendance, Lesson

    courses = Course.objects.filter(teacher=instructor)
    course_ids = list(courses.values_list('id', flat=True))
    data['groups_count'] = courses.exclude(status='finished').count()
    data['students_count'] = sum(c.active_students_count for c in courses)

    if not course_ids:
        return data

    # O'tilgan darslar va ishlagan kunlar (shu oyda)
    lessons = Lesson.objects.filter(course_id__in=course_ids, date__year=year, date__month=month)
    data['lessons_count'] = lessons.count()
    data['worked_days'] = lessons.values('date').distinct().count()
    # Taxminiy ishlagan soat: har dars ~2 soat
    data['worked_hours'] = Decimal(data['lessons_count'] * 2)

    # Guruhlardagi o'quvchilar davomati (shu oyda)
    att = Attendance.objects.filter(course_id__in=course_ids, date__year=year, date__month=month)
    total = att.count()
    if total:
        present = att.filter(status__in=['present', 'late']).count()
        data['attendance_rate'] = (Decimal(present) / Decimal(total) * 100).quantize(Decimal('0.01'))

    # O'rtacha o'zlashtirish
    from django.db.models import Avg
    avg = Assessment.objects.filter(
        course_id__in=course_ids, date__year=year, date__month=month
    ).aggregate(a=Avg('percentage'))['a']
    if avg:
        data['avg_score'] = Decimal(str(avg)).quantize(Decimal('0.01'))

    return data
