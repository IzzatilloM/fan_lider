from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.finance_dashboard, name='dashboard'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/new/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/generate/', views.invoice_generate, name='invoice_generate'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('debtors/', views.debtors, name='debtors'),
]
