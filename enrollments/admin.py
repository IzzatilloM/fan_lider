from django.contrib import admin

from .models import Enrollment, RegistrationApplication


@admin.register(RegistrationApplication)
class RegistrationApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'subject', 'source', 'status', 'created_at')
    list_filter = ('status', 'source', 'subject')
    search_fields = ('full_name', 'phone')
    list_editable = ('status',)
    date_hierarchy = 'created_at'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'monthly_fee', 'discount_percent', 'status', 'start_date')
    list_filter = ('status', 'course')
    search_fields = ('student__first_name', 'student__last_name')
    autocomplete_fields = ('student', 'course')
