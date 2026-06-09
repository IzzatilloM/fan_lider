from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('director/', views.director, name='director'),
    path('teacher/', views.teacher, name='teacher'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/<int:pk>/', views.teacher, name='teacher_preview'),
    path('teacher/<int:pk>/students/', views.teacher_students, name='teacher_students_preview'),
]
