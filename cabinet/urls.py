from django.urls import path

from . import views

app_name = 'cabinet'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('photo/', views.upload_photo, name='upload_photo'),
    path('student/<slug:slug>/', views.admin_view, name='admin_view'),
    path('telegram/webhook/', views.telegram_webhook, name='telegram_webhook'),
]
