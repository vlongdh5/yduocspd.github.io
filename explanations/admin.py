from django.contrib import admin
from .models import ExplanationReason, Explanation


@admin.register(ExplanationReason)
class ExplanationReasonAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'record', 'overall_status', 'submitted_at']
    list_filter = ['ci_status', 'co_status']
