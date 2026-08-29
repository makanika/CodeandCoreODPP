from django.contrib import admin

from .models import ConductComplaint, ConductDetermination, ConductEvent, ConductSequence


@admin.register(ConductComplaint)
class ConductComplaintAdmin(admin.ModelAdmin):
	list_display = ('reference', 'subject_officer_name', 'allegation_category', 'severity', 'status', 'assigned_investigator_name', 'received_at')
	list_filter = ('status', 'severity', 'allegation_category', 'is_demo')
	search_fields = ('reference', 'subject_officer_name', 'subject_officer_number', 'complainant_name')
	readonly_fields = ('reference', 'received_at', 'last_meaningful_update_at')


admin.site.register(ConductSequence)
admin.site.register(ConductEvent)
admin.site.register(ConductDetermination)
