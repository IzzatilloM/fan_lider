from django.contrib import admin

from .models import Assessment, Attendance, Lesson


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date', 'status')
    list_filter = ('status', 'date', 'course')
    search_fields = ('student__first_name', 'student__last_name')
    date_hierarchy = 'date'


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'type', 'title', 'score', 'max_score', 'percentage', 'date')
    list_filter = ('type', 'date', 'course')
    search_fields = ('student__first_name', 'student__last_name', 'title')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('course', 'date', 'topic')
    list_filter = ('course', 'date')
    search_fields = ('topic',)
