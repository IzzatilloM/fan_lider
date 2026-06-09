from django.contrib import admin

from .models import CenterProfile


@admin.register(CenterProfile)
class CenterProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address', 'updated_at')
