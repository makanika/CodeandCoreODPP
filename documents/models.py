from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models


def document_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f'documents/{instance.reference}{suffix}'


class Document(models.Model):
    class Category(models.TextChoices):
        COMPLAINT_EVIDENCE = 'COMPLAINT_EVIDENCE', 'Complaint evidence'
        CORRESPONDENCE = 'CORRESPONDENCE', 'Correspondence'
        REVIEW_NOTE = 'REVIEW_NOTE', 'Review note'
        DETERMINATION = 'DETERMINATION', 'Determination'
        COMMUNICATION_PROOF = 'COMMUNICATION_PROOF', 'Communication proof'
        FORM = 'FORM', 'Form'

    class Visibility(models.TextChoices):
        INTERNAL = 'INTERNAL', 'Internal'
        RESTRICTED = 'RESTRICTED', 'Restricted'
        CONFIDENTIAL = 'CONFIDENTIAL', 'Confidential'

    class ProcessingStatus(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SCANNING = 'SCANNING', 'Scanning'
        INDEXED = 'INDEXED', 'Indexed'
        FAILED = 'FAILED', 'Failed'
        QUARANTINED = 'QUARANTINED', 'Quarantined'

    reference = models.UUIDField(default=uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=document_upload_path)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    file_size = models.PositiveBigIntegerField()
    content_hash = models.CharField(max_length=128, unique=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.RESTRICTED)
    processing_status = models.CharField(max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.QUEUED)
    description = models.CharField(max_length=240, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(blank=True)
    ocr_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    requires_manual_verification = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_filename


class DocumentProcessingAttempt(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='processing_attempts')
    status = models.CharField(max_length=16, choices=Document.ProcessingStatus.choices)
    recorded_at = models.DateTimeField(auto_now_add=True)
    detail = models.CharField(max_length=500, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='document_processing_attempts')

    class Meta:
        ordering = ['-recorded_at']


class DocumentComment(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='document_comments')
    author_name = models.CharField(max_length=160, editable=False)
    author_officer_number = models.CharField(max_length=50, blank=True, editable=False)
    author_role = models.CharField(max_length=32, blank=True, editable=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    corrects = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='corrections')
    supporting_documents = models.ManyToManyField(Document, blank=True, related_name='attached_to_comments')

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.pk:
            profile = getattr(self.author, 'staff_profile', None)
            self.author_name = self.author.get_full_name() or self.author.username
            if profile:
                self.author_officer_number = profile.officer_number
                self.author_role = profile.role
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Comment by {self.author_name}'