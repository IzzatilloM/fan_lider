from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required
from cabinet.telegram import notify_student_credentials
from students.models import Student
from students.services import create_or_reset_login

from .forms import ApplicationStatusForm, EnrollmentForm, PublicApplicationForm
from .models import Enrollment, RegistrationApplication


# ============================ OMMAVIY (PUBLIC) ============================= #
def apply_public(request):
    """Tizimga kirmasdan ariza qoldirish — onlayn ro'yxatdan o'tish."""
    from courses.models import Course, Subject
    form = PublicApplicationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return render(request, 'enrollments/apply_success.html')
    return render(request, 'enrollments/apply_public.html', {
        'form': form,
        'subjects': Subject.objects.filter(is_active=True),
        'courses': Course.objects.filter(status='recruiting').select_related('subject'),
    })


# ============================ XODIM (CRM) ================================== #
@staff_required
def application_list(request):
    apps = RegistrationApplication.objects.select_related(
        'subject', 'assigned_to', 'converted_student'
    )
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        apps = apps.filter(status=status)
    if q:
        apps = apps.filter(Q(full_name__icontains=q) | Q(phone__icontains=q))

    base = RegistrationApplication.objects.all()
    counts = {row['status']: row['c'] for row in base.values('status').annotate(c=Count('id'))}
    context = {
        'applications': apps,
        'status': status,
        'q': q,
        'status_choices': RegistrationApplication.STATUS_CHOICES,
        'counts': counts,
        'total': base.count(),
        'new_count': counts.get('new', 0),
    }
    return render(request, 'enrollments/application_list.html', context)


@staff_required
def application_detail(request, pk):
    application = get_object_or_404(RegistrationApplication, pk=pk)
    form = ApplicationStatusForm(request.POST or None, instance=application)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Ariza holati yangilandi."))
        return redirect('enrollments:application_detail', pk=pk)
    return render(request, 'enrollments/application_detail.html', {
        'application': application, 'form': form,
    })


@manager_required
def application_convert(request, pk):
    """Arizani o'quvchiga aylantirish."""
    application = get_object_or_404(RegistrationApplication, pk=pk)
    if application.converted_student:
        messages.info(request, _("Bu ariza allaqachon o'quvchiga aylantirilgan."))
        return redirect('students:detail', slug=application.converted_student.slug)

    if request.method == 'POST':
        parts = application.full_name.split(' ', 1)
        student = Student.objects.create(
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else '',
            phone=application.phone,
            parent_phone=application.parent_phone,
            telegram_chat_id=application.telegram_chat_id,
            note=_("Onlayn arizadan (%(source)s).") % {'source': application.get_source_display()},
        )
        application.converted_student = student
        application.status = 'enrolled'
        application.save()

        if application.preferred_course:
            Enrollment.objects.get_or_create(
                student=student, course=application.preferred_course,
                defaults={'monthly_fee': application.preferred_course.monthly_fee},
            )

        # Tasdiqlash bilan birga shaxsiy kabinet logini yaratamiz va,
        # agar o'quvchi bot orqali kelgan bo'lsa (telegram_chat_id bor),
        # havola + login + parol avtomatik botga yuboriladi.
        username, password, _created = create_or_reset_login(student)
        cabinet_url = request.build_absolute_uri('/cabinet/')
        sent = notify_student_credentials(student, username, password, cabinet_url=cabinet_url)
        if sent:
            messages.success(
                request,
                _("%(name)s tasdiqlandi. Shaxsiy kabinet havolasi, login "
                  "(%(username)s) va parol o'quvchining Telegram'iga yuborildi.")
                % {'name': student.full_name, 'username': username},
            )
        else:
            messages.success(
                request,
                _("%(name)s o'quvchilarga qo'shildi. Login: %(username)s · "
                  "Parol: %(password)s (Telegram ulanmagani uchun bu ma'lumotni o'zingiz yetkazing).")
                % {'name': student.full_name, 'username': username, 'password': password},
            )
        return redirect('students:detail', slug=student.slug)

    return render(request, 'enrollments/application_convert.html', {'application': application})


# ============================ YOZILISHLAR ================================== #
@staff_required
def enrollment_list(request):
    enrollments = Enrollment.objects.select_related('student', 'course__subject')
    status = request.GET.get('status', '')
    if status:
        enrollments = enrollments.filter(status=status)
    return render(request, 'enrollments/enrollment_list.html', {
        'enrollments': enrollments,
        'status': status,
        'status_choices': Enrollment.STATUS_CHOICES,
        'active_count': Enrollment.objects.filter(status='active').count(),
    })


@staff_required
def enrollment_create(request):
    initial = {}
    if request.GET.get('student'):
        initial['student'] = request.GET['student']
    if request.GET.get('course'):
        initial['course'] = request.GET['course']
    form = EnrollmentForm(request.POST or None, initial=initial)
    if form.is_valid():
        enrollment = form.save()
        messages.success(request, _("O'quvchi guruhga yozildi."))
        return redirect('students:detail', slug=enrollment.student.slug)
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yangi yozilish")})


@staff_required
def enrollment_edit(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    form = EnrollmentForm(request.POST or None, instance=enrollment)
    if form.is_valid():
        form.save()
        messages.success(request, _("Yozilish yangilandi."))
        return redirect('students:detail', slug=enrollment.student.slug)
    return render(request, 'shared/object_form.html', {
        'form': form, 'title': _("Yozilishni tahrirlash"), 'enrollment': enrollment,
    })


@manager_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    slug = enrollment.student.slug
    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, _("Yozilish o'chirildi."))
        return redirect('students:detail', slug=slug)
    return render(request, 'shared/confirm_delete.html', {'object': enrollment, 'type': _("Yozilish")})
