"""Mobil ilova API marshrutlari (/api/...)."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'api'

urlpatterns = [
    # --- Auth ---
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.me, name='me'),

    # --- O'quvchi paneli ---
    path('student/overview/', views.student_overview, name='student_overview'),
    path('student/grades/', views.student_grades, name='student_grades'),
    path('student/attendance/', views.student_attendance, name='student_attendance'),
    path('student/payments/', views.student_payments, name='student_payments'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('student/profile/', views.student_profile_update, name='student_profile_update'),

    # --- O'qituvchi paneli ---
    path('teacher/overview/', views.teacher_overview, name='teacher_overview'),
    path('teacher/profile/', views.teacher_profile_update, name='teacher_profile_update'),
    path('teacher/groups/', views.teacher_groups, name='teacher_groups'),
    path('teacher/groups/<int:course_id>/students/', views.teacher_group_students,
         name='teacher_group_students'),
    path('teacher/schedule/', views.teacher_schedule, name='teacher_schedule'),
]
