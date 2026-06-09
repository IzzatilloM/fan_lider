from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, PasswordResetRequest, TelegramVerificationCode


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_verified', 'is_active')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'telegram_chat_id')
    list_editable = ('role',)
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha", {'fields': ('role', 'phone', 'avatar', 'telegram_chat_id',
                                    'is_verified', 'plain_password', 'must_change_password')}),
    )


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'role', 'status', 'matched_user', 'created_at', 'resolved_at')
    list_filter = ('role', 'status')
    search_fields = ('identifier', 'full_name', 'telegram_chat_id')
    ordering = ('-created_at',)


@admin.register(TelegramVerificationCode)
class TelegramVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'code', 'purpose', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('chat_id',)
    ordering = ('-created_at',)
