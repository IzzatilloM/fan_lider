import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required

from .forms import InstructorCreateForm, InstructorUpdateForm, suggest_teacher_username
from .models import Instructor

User = get_user_model()


@staff_required
def instructor_list(request):
    instructors = Instructor.objects.select_related('user').all()
    return render(request, 'instructors/instructor_list.html', {
        'instructors': instructors,
        'active_count': instructors.filter(is_active=True).count(),
        'total_count': instructors.count(),
    })


@staff_required
def instructor_detail(request, pk):
    instructor = get_object_or_404(Instructor.objects.select_related('user'), pk=pk)
    groups = instructor.courses.select_related('subject').all()
    return render(request, 'instructors/instructor_detail.html', {
        'instructor': instructor,
        'groups': groups,
    })


@manager_required
def instructor_create(request):
    """Yangi o'qituvchi qo'shadi va unga kabinet logini yaratadi.

    `role='teacher'` user yaratiladi → signal `Instructor` profilini hosil qiladi,
    keyin profil qo'shimcha maydonlar bilan to'ldiriladi. Login va parol bir marta
    ko'rsatiladi.
    """
    form = InstructorCreateForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        username = cd['username'].strip() or suggest_teacher_username(
            cd['first_name'], cd['last_name'])
        password = (cd['password'] or '').strip() or secrets.token_urlsafe(6)

        user = User.objects.create_user(
            username=username,
            password=password,
            role='teacher',
            first_name=cd['first_name'],
            last_name=cd['last_name'] or '',
            email=cd['email'] or '',
            phone=cd['phone'] or '',
            plain_password=password,
        )
        # Signal Instructor profilini yaratdi — qolgan maydonlarni to'ldiramiz
        instructor = user.instructor_profile
        instructor.full_name = f"{cd['first_name']} {cd['last_name'] or ''}".strip() or username
        instructor.phone = cd['phone'] or ''
        instructor.email = cd['email'] or ''
        instructor.specialty = cd['specialty'] or ''
        instructor.experience_years = cd['experience_years'] or 0
        instructor.salary = cd['salary'] or 0
        instructor.bio = cd['bio'] or ''
        if cd.get('image'):
            instructor.image = cd['image']
        instructor.save()

        messages.success(
            request,
            _("✅ O'qituvchi «%(name)s» qo'shildi. "
              "Kirish — Login: %(username)s · Parol: %(password)s "
              "(ushbu ma'lumotni o'qituvchiga yetkazing).")
            % {'name': instructor.full_name, 'username': username, 'password': password},
        )
        return redirect('instructors:detail', pk=instructor.pk)
    return render(request, 'instructors/instructor_form.html', {
        'form': form, 'create': True,
    })


@manager_required
def instructor_edit(request, pk):
    instructor = get_object_or_404(Instructor, pk=pk)
    form = InstructorUpdateForm(request.POST or None, request.FILES or None, instance=instructor)
    if form.is_valid():
        inst = form.save()
        user = inst.user
        parts = (inst.full_name or '').split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        if inst.email:
            user.email = inst.email
        if inst.phone:
            user.phone = inst.phone
        user.is_active = inst.is_active
        user.save()
        messages.success(request, _("O'qituvchi ma'lumotlari yangilandi."))
        return redirect('instructors:detail', pk=inst.pk)
    return render(request, 'shared/object_form.html', {
        'form': form, 'instructor': instructor,
    })


@manager_required
def instructor_delete(request, pk):
    instructor = get_object_or_404(Instructor, pk=pk)
    if request.method == 'POST':
        user = instructor.user
        user.role = 'student'
        user.save()  # signal Instructor profilini o'chiradi
        messages.success(request, _("O'qituvchi ro'yxatdan chiqarildi."))
        return redirect('instructors:list')
    return render(request, 'shared/confirm_delete.html', {'object': instructor, 'type': _("O'qituvchi")})
