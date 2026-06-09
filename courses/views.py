from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required

from .forms import CourseForm, SubjectForm
from .models import Course, Subject


@login_required
def course_list(request):
    qs = Course.objects.select_related('subject', 'teacher__user').annotate(
        students=Count('enrollments', filter=Q(enrollments__status='active'))
    )
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    subject_id = request.GET.get('subject', '')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(subject__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    context = {
        'courses': qs,
        'subjects': Subject.objects.filter(is_active=True),
        'q': q,
        'status': status,
        'subject_id': subject_id,
        'status_choices': Course.STATUS_CHOICES,
    }
    return render(request, 'courses/course_list.html', context)


@login_required
def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related('subject', 'teacher__user'), slug=slug
    )
    enrollments = course.enrollments.select_related('student').filter(
        status='active'
    )
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'enrollments': enrollments,
    })


@staff_required
def course_create(request):
    form = CourseForm(request.POST or None)
    if form.is_valid():
        course = form.save()
        messages.success(request, _("'%(name)s' guruhi yaratildi.") % {'name': course.name})
        return redirect('courses:detail', slug=course.slug)
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yangi guruh")})


@staff_required
def course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug)
    form = CourseForm(request.POST or None, instance=course)
    if form.is_valid():
        form.save()
        messages.success(request, _("Guruh ma'lumotlari yangilandi."))
        return redirect('courses:detail', slug=course.slug)
    return render(request, 'shared/object_form.html', {
        'form': form, 'title': _("Tahrirlash — %(name)s") % {'name': course.name}, 'course': course,
    })


@manager_required
def course_delete(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == 'POST':
        course.delete()
        messages.success(request, _("Guruh o'chirildi."))
        return redirect('courses:list')
    return render(request, 'shared/confirm_delete.html', {'object': course, 'type': _('Guruh')})


# --------------------------- Yo'nalishlar (Subject) ------------------------ #
@login_required
def subject_list(request):
    subjects = Subject.objects.annotate(course_count=Count('courses'))
    return render(request, 'courses/subject_list.html', {'subjects': subjects})


@staff_required
def subject_create(request):
    form = SubjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, _("Yo'nalish qo'shildi."))
        return redirect('courses:subject_list')
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yangi yo'nalish")})


@staff_required
def subject_edit(request, slug):
    subject = get_object_or_404(Subject, slug=slug)
    form = SubjectForm(request.POST or None, instance=subject)
    if form.is_valid():
        form.save()
        messages.success(request, _("Yo'nalish yangilandi."))
        return redirect('courses:subject_list')
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yo'nalishni tahrirlash")})
