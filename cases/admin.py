from django.contrib import admin
from .models import CaseAssignment, CaseDocumentLink, CaseIdentifier, CaseMovement, CaseReference

@admin.register(CaseReference)
class CaseReferenceAdmin(admin.ModelAdmin):
	list_display = ('reference', 'title', 'stage', 'sensitivity', 'originating_station', 'current_office', 'allocated_to')
	list_filter = ('stage', 'sensitivity', 'responsible_region', 'is_demo')
	search_fields = ('reference', 'title', 'complaint_context')

admin.site.register(CaseIdentifier)
admin.site.register(CaseMovement)
admin.site.register(CaseAssignment)
admin.site.register(CaseDocumentLink)

# Register your models here.
