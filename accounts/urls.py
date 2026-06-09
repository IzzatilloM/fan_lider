from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_page, name='login_page'),
    path('register/', views.register, name='register'),
    path('verify/', views.verify, name='verify'),
    path('resend/', views.resend_code, name='resend'),
    path('forgot/', views.forgot_password, name='forgot_password'),
    path('reset/', views.reset_password, name='reset_password'),
    path('force-password/', views.force_password, name='force_password'),
    path('reset-help/', views.reset_help, name='reset_help'),
    path('reset-requests/', views.reset_requests, name='reset_requests'),
    path('reset-requests/<int:pk>/resolve/', views.reset_request_resolve, name='reset_request_resolve'),

    # Admin: foydalanuvchilarni boshqarish
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/password/', views.user_set_password, name='user_set_password'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/impersonate/', views.impersonate, name='impersonate'),
    path('stop-impersonation/', views.stop_impersonation, name='stop_impersonation'),

    # Admin: sozlamalar (o'z paroli, markaz ma'lumotlari, loginlar)
    path('settings/', views.settings_home, name='settings_home'),
    path('settings/password/', views.settings_password, name='settings_password'),
    path('settings/center/', views.settings_center, name='settings_center'),

    path('profile/', views.profile, name='profile'),
    path('avatar/', views.upload_avatar, name='upload_avatar'),
    path('signout/', views.logout_view, name='logout'),
]
