from django.contrib import admin
from .models import CaseAssignment, CaseComment, CaseDocumentLink, CaseIdentifier, CaseMovement, CaseParty, CaseReference

@admin.register(CaseReference)
class CaseReferenceAdmin(admin.ModelAdmin):
	list_display = ('reference', 'title', 'stage', 'sensitivity', 'originating_station', 'current_office', 'allocated_to')
	list_filter = ('stage', 'sensitivity', 'responsible_region', 'is_demo')
	search_fields = ('reference', 'title', 'complaint_context')

@admin.register(CaseParty)
class CasePartyAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'role', 'case', 'nin', 'phone')
	list_filter = ('role',)
	search_fields = ('full_name', 'nin', 'case__reference')

admin.site.register(CaseIdentifier)
admin.site.register(CaseMovement)
admin.site.register(CaseAssignment)
admin.site.register(CaseDocumentLink)
admin.site.register(CaseComment)

# Register your models here.
