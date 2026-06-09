from django.urls import path

from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.monitoring_home, name='home'),
    path('grades/new/', views.assessment_create, name='assessment_create'),
    path('grades/<int:pk>/delete/', views.assessment_delete, name='assessment_delete'),
    path('student/<slug:slug>/report/', views.student_report, name='student_report'),
    path('<slug:slug>/attendance/', views.attendance_take, name='attendance_take'),
    path('<slug:slug>/journal/', views.attendance_journal, name='attendance_journal'),
    path('<slug:slug>/grades/', views.grade_book, name='grade_book'),
    path('<slug:slug>/lessons/', views.lesson_journal, name='lesson_journal'),
]
