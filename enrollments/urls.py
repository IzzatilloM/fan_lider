from django.urls import path

from . import views

app_name = 'enrollments'

urlpatterns = [
    # Ommaviy onlayn ariza
    path('apply/', views.apply_public, name='apply'),

    # Arizalar (CRM)
    path('applications/', views.application_list, name='application_list'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/convert/', views.application_convert, name='application_convert'),

    # Yozilishlar
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/new/', views.enrollment_create, name='enrollment_create'),
    path('enrollments/<int:pk>/edit/', views.enrollment_edit, name='enrollment_edit'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
]
