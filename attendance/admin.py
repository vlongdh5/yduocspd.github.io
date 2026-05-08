from django.contrib import admin
from .models import AttendanceUpload, AttendanceRecord, ErrorType


@admin.register(ErrorType)
class ErrorTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_editable = ['is_active']


@admin.register(AttendanceUpload)
class AttendanceUploadAdmin(admin.ModelAdmin):
    list_display = ['month', 'uploaded_by', 'status', 'total_records', 'error_records', 'uploaded_at']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter = ['status', 'upload__month']
