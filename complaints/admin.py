from django.contrib import admin

from .models import Complaint, ComplaintAssignment, ComplaintCommunication, ComplaintDetermination, ComplaintDocument, ComplaintEvent, ComplaintInquiry, ComplaintSequence, FileRecallOrder


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
	list_display = ('reference', 'classification', 'status', 'priority', 'stakeholder_role', 'related_case', 'assigned_to', 'sla_due_at', 'received_at')
	list_filter = ('classification', 'status', 'priority', 'intake_channel', 'stakeholder_role', 'is_demo')
	search_fields = ('reference', 'supplied_case_reference', 'related_case__reference')
	readonly_fields = ('reference', 'tracking_pin_hash', 'qr_locator_id', 'received_at', 'last_meaningful_update_at')


admin.site.register(ComplaintSequence)
admin.site.register(ComplaintAssignment)
admin.site.register(ComplaintInquiry)
admin.site.register(ComplaintDetermination)
admin.site.register(ComplaintCommunication)
admin.site.register(ComplaintDocument)
admin.site.register(ComplaintEvent)
admin.site.register(FileRecallOrder)
