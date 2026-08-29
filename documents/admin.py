from django.contrib import admin

from .models import Document, DocumentComment, DocumentProcessingAttempt


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'category', 'visibility', 'processing_status', 'uploaded_by', 'uploaded_at')
    list_filter = ('category', 'visibility', 'processing_status')
    search_fields = ('original_filename', 'content_hash', 'description')
    readonly_fields = ('reference', 'uploaded_at')


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    list_display = ('document', 'author_name', 'author_officer_number', 'author_role', 'created_at')
    readonly_fields = ('author_name', 'author_officer_number', 'author_role', 'created_at')


admin.site.register(DocumentProcessingAttempt)