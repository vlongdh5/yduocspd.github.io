from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SystemConfig


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name_display', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['email']
    ordering = ['email']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & OTP', {'fields': ('role', 'extra_roles', 'otp_method')}),
    )

    def full_name_display(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip() or '—'
    full_name_display.short_description = 'Họ tên'


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value']
