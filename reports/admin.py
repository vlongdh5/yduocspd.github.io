from django.contrib import admin
from .models import AttendanceCalculation

@admin.register(AttendanceCalculation)
class AttendanceCalculationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'actual_workdays', 'leave_days_used', 'status']
    list_filter = ['month', 'status']
