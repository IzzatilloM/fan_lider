from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Invoice, Payment


def recompute_student_balance(student):
    if student is None:
        return
    invoiced = student.invoices.exclude(status='cancelled').aggregate(
        s=Sum('amount'))['s'] or Decimal('0')
    paid = student.payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    student.balance = paid - invoiced
    student.save(update_fields=['balance'])


@receiver(post_save, sender=Payment)
def payment_saved(sender, instance, **kwargs):
    if instance.invoice:
        instance.invoice.recalc()
    recompute_student_balance(instance.student)


@receiver(post_delete, sender=Payment)
def payment_deleted(sender, instance, **kwargs):
    if instance.invoice_id:
        try:
            instance.invoice.recalc()
        except Invoice.DoesNotExist:
            pass
    recompute_student_balance(instance.student)


@receiver(post_save, sender=Invoice)
def invoice_saved(sender, instance, **kwargs):
    recompute_student_balance(instance.student)


@receiver(post_delete, sender=Invoice)
def invoice_deleted(sender, instance, **kwargs):
    recompute_student_balance(instance.student)
