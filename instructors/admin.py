from django.contrib import admin

from .models import Instructor


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'specialty', 'experience_years', 'salary', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('full_name', 'user__username', 'email', 'phone', 'specialty')
