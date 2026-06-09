import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.decorators import manager_required, staff_required
from enrollments.models import Enrollment
from students.models import Student

from .forms import GenerateInvoicesForm, InvoiceForm, PaymentForm
from .models import UZB_MONTHS, Invoice, Payment
from .receipt import build_payment_receipt


@login_required
def payment_receipt(request, pk):
    """To'lov chekini PDF sifatida yuklab beradi.

    Xodimlar — har qanday chekni; o'quvchi — faqat o'zinikini.
    """
    payment = get_object_or_404(Payment.objects.select_related('student', 'invoice__course', 'received_by'), pk=pk)
    u = request.user
    is_staff = u.is_superuser or u.is_staff_role
    is_owner = payment.student.user_id == u.id
    if not (is_staff or is_owner):
        raise PermissionDenied("Bu chekka ruxsat yo'q.")

    pdf = build_payment_receipt(payment)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="chek-{payment.pk}.pdf"'
    return resp


@manager_required
def finance_dashboard(request):
    today = timezone.now()
    month_payments = Payment.objects.filter(
        paid_at__year=today.year, paid_at__month=today.month
    )
    total_month = month_payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_all = Payment.objects.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    debtors_qs = Student.objects.filter(balance__lt=0)
    total_debt = abs(debtors_qs.aggregate(s=Sum('balance'))['s'] or Decimal('0'))

    unpaid_invoices = Invoice.objects.exclude(status__in=['paid', 'cancelled'])

    monthly_series = []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + (today.month - i - 1) // 12
        amount = Payment.objects.filter(paid_at__year=y, paid_at__month=m).aggregate(
            s=Sum('amount'))['s'] or 0
        monthly_series.append({'label': UZB_MONTHS[m - 1][:3], 'value': float(amount)})

    by_method = month_payments.values('method').annotate(s=Sum('amount'), c=Count('id'))

    context = {
        'total_month': total_month,
        'total_all': total_all,
        'debtors_count': debtors_qs.count(),
        'total_debt': total_debt,
        'unpaid_count': unpaid_invoices.count(),
        'payments_count': month_payments.count(),
        'monthly_series': monthly_series,
        'by_method': by_method,
        'recent_payments': Payment.objects.select_related('student').all()[:8],
        'top_debtors': debtors_qs.order_by('balance')[:8],
    }
    return render(request, 'payments/finance_dashboard.html', context)


@staff_required
def payment_list(request):
    payments = Payment.objects.select_related('student', 'invoice', 'received_by')
    q = request.GET.get('q', '').strip()
    method = request.GET.get('method', '')
    if q:
        payments = payments.filter(
            Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q)
        )
    if method:
        payments = payments.filter(method=method)
    total = payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    return render(request, 'payments/payment_list.html', {
        'payments': payments[:300],
        'q': q,
        'method': method,
        'method_choices': Payment.METHOD_CHOICES,
        'total': total,
    })


@manager_required
def payment_create(request):
    initial = {'paid_at': timezone.now().strftime('%Y-%m-%dT%H:%M')}
    if request.GET.get('student'):
        initial['student'] = request.GET['student']
    if request.GET.get('invoice'):
        inv = Invoice.objects.filter(pk=request.GET['invoice']).first()
        if inv:
            initial['invoice'] = inv.pk
            initial['student'] = inv.student_id
            initial['amount'] = inv.remaining
    form = PaymentForm(request.POST or None, initial=initial)
    if form.is_valid():
        payment = form.save(commit=False)
        payment.received_by = request.user
        payment.save()
        messages.success(request, _("%(amount)s so'm to'lov qabul qilindi.") % {'amount': payment.amount})
        return redirect('payments:payment_list')
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("To'lov qabul qilish")})


@manager_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, _("To'lov o'chirildi."))
        return redirect('payments:payment_list')
    return render(request, 'shared/confirm_delete.html', {'object': payment, 'type': _("To'lov")})


@staff_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('student', 'course')
    status = request.GET.get('status', '')
    if status == 'overdue':
        invoices = invoices.exclude(status__in=['paid', 'cancelled']).filter(
            due_date__lt=timezone.now().date())
    elif status:
        invoices = invoices.filter(status=status)
    return render(request, 'payments/invoice_list.html', {
        'invoices': invoices[:300],
        'status': status,
        'status_choices': Invoice.STATUS_CHOICES,
        'unpaid_total': Invoice.objects.exclude(status__in=['paid', 'cancelled']).aggregate(
            s=Sum('amount'))['s'] or Decimal('0'),
    })


@manager_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None)
    if form.is_valid():
        invoice = form.save(commit=False)
        invoice.created_by = request.user
        invoice.save()
        messages.success(request, _("Hisob-faktura yaratildi."))
        return redirect('payments:invoice_list')
    return render(request, 'shared/object_form.html', {'form': form, 'title': _("Yangi hisob-faktura")})


@manager_required
def invoice_generate(request):
    form = GenerateInvoicesForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        year = form.cleaned_data['year']
        month = int(form.cleaned_data['month'])
        due_day = form.cleaned_data['due_day']
        due_date = datetime.date(year, month, min(due_day, 28))

        enrollments = Enrollment.objects.filter(status='active').select_related('student', 'course')
        created = 0
        skipped = 0
        for en in enrollments:
            exists = Invoice.objects.filter(
                student=en.student, enrollment=en, year=year, month=month
            ).exists()
            if exists:
                skipped += 1
                continue
            Invoice.objects.create(
                student=en.student,
                enrollment=en,
                course=en.course,
                year=year,
                month=month,
                amount=en.net_fee,
                due_date=due_date,
                created_by=request.user,
            )
            created += 1
        messages.success(
            request,
            _("%(created)s ta hisob-faktura yaratildi. %(skipped)s ta allaqachon mavjud edi.")
            % {'created': created, 'skipped': skipped},
        )
        return redirect('payments:invoice_list')
    return render(request, 'payments/invoice_generate.html', {'form': form})


@manager_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, _("Hisob-faktura o'chirildi."))
        return redirect('payments:invoice_list')
    return render(request, 'shared/confirm_delete.html', {'object': invoice, 'type': _("Hisob-faktura")})


@staff_required
def debtors(request):
    debtor_qs = Student.objects.filter(balance__lt=0).order_by('balance')
    total_debt = abs(debtor_qs.aggregate(s=Sum('balance'))['s'] or Decimal('0'))
    return render(request, 'payments/debtors.html', {
        'debtors': debtor_qs,
        'total_debt': total_debt,
        'count': debtor_qs.count(),
    })
