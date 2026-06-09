from django.urls import path

from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list, name='list'),
    path('new/', views.student_create, name='create'),
    path('<slug:slug>/', views.student_detail, name='detail'),
    path('<slug:slug>/edit/', views.student_update, name='update'),
    path('<slug:slug>/login/', views.student_login_create, name='login_create'),
    path('<slug:slug>/delete/', views.student_delete, name='delete'),
]
