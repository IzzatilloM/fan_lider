from django.contrib import admin

from .models import Employee, SalaryPeriod, SalaryRecord


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'employment_type', 'base_salary', 'is_active')
    list_filter = ('position', 'employment_type', 'is_active')
    search_fields = ('full_name', 'user__email', 'card_number')


class SalaryRecordInline(admin.TabularInline):
    model = SalaryRecord
    extra = 0
    fields = ('employee', 'total_amount', 'kpi_score', 'ai_rating', 'status')
    readonly_fields = ('employee', 'total_amount', 'kpi_score', 'ai_rating')


@admin.register(SalaryPeriod)
class SalaryPeriodAdmin(admin.ModelAdmin):
    list_display = ('label', 'status', 'total_payout', 'created_at')
    list_filter = ('status', 'year')
    inlines = [SalaryRecordInline]


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'period', 'total_amount', 'kpi_score', 'ai_rating', 'status')
    list_filter = ('status', 'ai_generated', 'period')
    search_fields = ('employee__full_name',)
