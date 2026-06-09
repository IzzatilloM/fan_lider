from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('new/', views.course_create, name='create'),
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/new/', views.subject_create, name='subject_create'),
    path('subjects/<slug:slug>/edit/', views.subject_edit, name='subject_edit'),
    path('<slug:slug>/', views.course_detail, name='detail'),
    path('<slug:slug>/edit/', views.course_edit, name='edit'),
    path('<slug:slug>/delete/', views.course_delete, name='delete'),
]
