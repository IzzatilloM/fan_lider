from django.contrib import admin

from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'month', 'year', 'amount', 'paid_amount', 'status', 'due_date')
    list_filter = ('status', 'year', 'month')
    search_fields = ('student__first_name', 'student__last_name')
    autocomplete_fields = ('student',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'method', 'paid_at', 'received_by')
    list_filter = ('method', 'paid_at')
    search_fields = ('student__first_name', 'student__last_name')
    autocomplete_fields = ('student',)
    date_hierarchy = 'paid_at'
