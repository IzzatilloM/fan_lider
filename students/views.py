from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required
from cabinet.telegram import notify_student_credentials

from .forms import StudentForm
from .models import Student
from .services import create_or_reset_login, suggest_username

User = get_user_model()


def _unique_username(student):
    return suggest_username(student)


@staff_required
def student_list(request):
    students = Student.objects.select_related('user').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    if q:
        students = students.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q)
        )
    if status:
        students = students.filter(status=status)

    all_students = Student.objects.all()
    context = {
        'students': students,
        'q': q,
        'status': status,
        'status_choices': Student.STATUS_CHOICES,
        'total': all_students.count(),
        'active': all_students.filter(status='active').count(),
        'debtors': all_students.filter(balance__lt=0).count(),
    }
    return render(request, 'students/student_list.html', context)


@staff_required
def student_detail(request, slug):
    student = get_object_or_404(Student, slug=slug)
    enrollments = student.enrollments.select_related('course__subject').all()
    payments = student.payments.select_related('invoice').order_by('-paid_at')[:10]
    assessments = student.assessments.select_related('course').order_by('-date')[:10]
    return render(request, 'students/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'payments': payments,
        'assessments': assessments,
        'suggested_username': _unique_username(student) if not student.user_id else '',
    })


@manager_required
def student_login_create(request, slug):
    """O'quvchi uchun kabinet logini (username + parol) yaratadi va bog'laydi.

    Parol bir marta ko'rsatiladi. Telegram ulangani bo'lsa, havola + parol
    avtomatik botga yuboriladi.
    """
    student = get_object_or_404(Student, slug=slug)
    if request.method != 'POST':
        return redirect('students:detail', slug=slug)

    username, password, created = create_or_reset_login(
        student,
        username=request.POST.get('username', ''),
        password=request.POST.get('password', ''),
    )
    action = _("yaratildi") if created else _("yangilandi")

    cabinet_url = request.build_absolute_uri('/cabinet/')
    sent = notify_student_credentials(student, username, password, cabinet_url=cabinet_url)
    if sent:
        messages.success(
            request,
            _("Kabinet logini %(action)s. Login va parol o'quvchining Telegram'iga yuborildi. "
              "Login: %(username)s · Parol: %(password)s")
            % {'action': action, 'username': username, 'password': password},
        )
    else:
        messages.success(
            request,
            _("Kabinet logini %(action)s. Login: %(username)s · Parol: %(password)s "
              "(Telegram ulanmagani uchun bu ma'lumotni o'quvchiga o'zingiz yetkazing).")
            % {'action': action, 'username': username, 'password': password},
        )
    return redirect('students:detail', slug=slug)


@staff_required
def student_create(request):
    form = StudentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        student = form.save()

        # Ixtiyoriy: o'quvchi qo'shilishi bilan kabinet logini yaratish
        if request.POST.get('create_login'):
            username, password, _created = create_or_reset_login(
                student,
                username=request.POST.get('username', ''),
                password=request.POST.get('password', ''),
            )
            cabinet_url = request.build_absolute_uri('/cabinet/')
            sent = notify_student_credentials(student, username, password, cabinet_url=cabinet_url)
            if sent:
                messages.success(
                    request,
                    _("%(name)s qo'shildi. Login (%(username)s) va parol "
                      "o'quvchining Telegram'iga yuborildi.")
                    % {'name': student.full_name, 'username': username},
                )
            else:
                messages.success(
                    request,
                    _("%(name)s qo'shildi. Kabinet logini — Login: %(username)s · "
                      "Parol: %(password)s (bu ma'lumotni o'quvchiga yetkazing).")
                    % {'name': student.full_name, 'username': username, 'password': password},
                )
        else:
            messages.success(request, _("%(name)s qo'shildi.") % {'name': student.full_name})
        return redirect('students:detail', slug=student.slug)
    return render(request, 'students/student_create.html', {'form': form, 'title': _("Yangi o'quvchi")})


@staff_required
def student_update(request, slug):
    student = get_object_or_404(Student, slug=slug)
    form = StudentForm(request.POST or None, request.FILES or None, instance=student)
    if form.is_valid():
        form.save()
        messages.success(request, _("Ma'lumotlar yangilandi."))
        return redirect('students:detail', slug=student.slug)
    return render(request, 'shared/object_form.html', {
        'form': form, 'title': _("Tahrirlash — %(name)s") % {'name': student.full_name}, 'student': student,
    })


@manager_required
def student_delete(request, slug):
    student = get_object_or_404(Student, slug=slug)
    if request.method == 'POST':
        student.delete()
        messages.success(request, _("O'quvchi o'chirildi."))
        return redirect('students:list')
    return render(request, 'shared/confirm_delete.html', {'object': student, 'type': _("O'quvchi")})
