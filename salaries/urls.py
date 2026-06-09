from django.urls import path

from . import views

app_name = 'salaries'

urlpatterns = [
    path('', views.home, name='home'),
    path('compute/', views.compute_period, name='compute'),
    path('ai/', views.period_ai_all, name='ai_all'),

    path('employees/', views.employee_list, name='employees'),
    path('employees/sync/', views.sync_employees, name='sync'),
    path('employees/new/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    path('record/<int:pk>/', views.record_detail, name='record_detail'),
    path('record/<int:pk>/metrics/', views.record_metrics, name='record_metrics'),
    path('record/<int:pk>/refresh/', views.record_refresh_auto, name='record_refresh'),
    path('record/<int:pk>/ai/', views.record_ai, name='record_ai'),
    path('record/<int:pk>/status/', views.record_set_status, name='record_status'),
    path('record/<int:pk>/payslip/', views.payslip, name='payslip'),
]
