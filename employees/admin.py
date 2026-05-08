from django.contrib import admin
from .models import Department, Employee, LeaveBalance, LeaveTransaction


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'manager']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'department', 'position', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['code', 'full_name']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'year', 'total_days', 'used_days', 'remaining_days']
    list_filter = ['year']
