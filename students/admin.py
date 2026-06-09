from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'grade', 'status', 'balance', 'created_at')
    list_filter = ('status', 'gender', 'grade')
    search_fields = ('first_name', 'last_name', 'phone', 'parent_phone')
    prepopulated_fields = {'slug': ('first_name', 'last_name')}
    readonly_fields = ('balance',)
