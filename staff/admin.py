from django.contrib import admin

from .models import StaffPosting, StaffProfile, StaffScopeAssignment


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('officer_number', 'account', 'organisation', 'role', 'job_title', 'rank', 'current_office', 'is_active')
    list_filter = ('organisation', 'role', 'is_active')
    search_fields = ('officer_number', 'account__username', 'account__first_name', 'account__last_name')


admin.site.register(StaffPosting)
admin.site.register(StaffScopeAssignment)