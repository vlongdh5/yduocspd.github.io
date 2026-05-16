from django.contrib import admin
from .models import Department, Employee, LeaveBalance, LeaveTransaction, CompensatoryBalance, CompensatoryTransaction


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


@admin.register(CompensatoryBalance)
class CompensatoryBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'total_hours', 'used_hours', 'remaining_hours']
    search_fields = ['employee__code', 'employee__full_name']


@admin.register(CompensatoryTransaction)
class CompensatoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'transaction_type', 'hours', 'date', 'created_by']
    list_filter = ['transaction_type']
