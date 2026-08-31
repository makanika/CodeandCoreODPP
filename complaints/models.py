from django.db import models

from uuid import uuid4

from django.conf import settings
from django.db import models

from cases.models import CaseParty, CaseReference
from common.models import Office
from documents.models import Document
from staff.models import StaffProfile


class ComplaintSequence(models.Model):
	year = models.PositiveSmallIntegerField(unique=True)
	next_value = models.PositiveIntegerField(default=1)


class Complaint(models.Model):
	class IntakeChannel(models.TextChoices):
		PUBLIC_PORTAL = 'PUBLIC_PORTAL', 'Public portal'
		CALL_CENTRE = 'CALL_CENTRE', 'Toll-free / call centre'
		ASSISTED_DESK = 'ASSISTED_DESK', 'Walk-in / assisted desk'
		MONITORED_EMAIL = 'MONITORED_EMAIL', 'Monitored email'

	class Classification(models.TextChoices):
		UNCLASSIFIED = 'UNCLASSIFIED', 'Awaiting classification'
		TYPE_B = 'TYPE_B', 'Type B - process complaint'
		TYPE_A_HANDOFF = 'TYPE_A_HANDOFF', 'Type A - transferred to conduct'

	class Status(models.TextChoices):
		RECEIVED = 'RECEIVED', 'Received'
		OPEN_RSA = 'OPEN_RSA', 'Open with responsible officer'
		RESOLVED_RSA = 'RESOLVED_RSA', 'Resolved by responsible officer'
		ESCALATED_REGIONAL = 'ESCALATED_REGIONAL', 'Escalated to regional review'
		RESOLVED_REGIONAL = 'RESOLVED_REGIONAL', 'Resolved by regional review'
		ESCALATED_HQ = 'ESCALATED_HQ', 'Escalated to headquarters'
		REINSTATED = 'REINSTATED', 'Reinstated by directive'
		SANCTIONED = 'SANCTIONED', 'Sanctioned by directive'
		WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
		REFERRED_OUT = 'REFERRED_OUT', 'Referred out'
		TYPE_A_HANDOFF = 'TYPE_A_HANDOFF', 'Transferred to Internal Affairs'

	class Priority(models.IntegerChoices):
		LOW = 1, 'Low'
		NORMAL = 2, 'Normal'
		HIGH = 3, 'High'
		URGENT = 4, 'Urgent'

	reference = models.CharField(max_length=32, unique=True, editable=False)
	tracking_pin_hash = models.CharField(max_length=256, editable=False)
	qr_locator_id = models.UUIDField(default=uuid4, unique=True, editable=False)
	intake_channel = models.CharField(max_length=20, choices=IntakeChannel.choices)
	received_at = models.DateTimeField(auto_now_add=True)
	captured_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='captured_complaints')
	source_evidence_reference = models.CharField(max_length=160, blank=True)
	complainant_name = models.CharField(max_length=160)
	complainant_nin = models.CharField(max_length=14, blank=True, verbose_name='Complainant NIN')
	complainant_phone = models.CharField(max_length=32, blank=True)
	complainant_email = models.EmailField(blank=True)
	preferred_contact_channel = models.CharField(max_length=20, blank=True)
	stakeholder_role = models.CharField(max_length=16, choices=CaseParty.Role.choices, blank=True)
	related_case = models.ForeignKey(CaseReference, null=True, blank=True, on_delete=models.PROTECT, related_name='complaints')
	supplied_case_reference = models.CharField(max_length=100, blank=True)
	subject = models.CharField(max_length=240)
	narrative = models.TextField()
	classification = models.CharField(max_length=20, choices=Classification.choices, default=Classification.UNCLASSIFIED)
	status = models.CharField(max_length=24, choices=Status.choices, default=Status.RECEIVED)
	priority = models.PositiveSmallIntegerField(choices=Priority.choices, default=Priority.NORMAL)
	assigned_to = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='assigned_complaints')
	assigned_office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.PROTECT, related_name='assigned_complaints')
	sla_due_at = models.DateTimeField(null=True, blank=True)
	acknowledged_at = models.DateTimeField(null=True, blank=True)
	last_meaningful_update_at = models.DateTimeField(auto_now_add=True)
	public_status = models.CharField(max_length=240, default='Your complaint has been received and is awaiting review.')
	type_a_handoff_reference = models.CharField(max_length=32, blank=True, editable=False)
	is_demo = models.BooleanField(default=False)

	class Meta:
		ordering = ['-last_meaningful_update_at', 'reference']

	def __str__(self):
		return self.reference


class ComplaintAssignment(models.Model):
	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='assignments')
	assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='complaint_assignment_history')
	assigned_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='assigned_complaint_history')
	assigned_at = models.DateTimeField(auto_now_add=True)
	ended_at = models.DateTimeField(null=True, blank=True)
	reason = models.CharField(max_length=300)
	priority = models.PositiveSmallIntegerField(choices=Complaint.Priority.choices)
	due_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-assigned_at']


class ComplaintInquiry(models.Model):
	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='inquiries')
	opened_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='opened_complaint_inquiries')
	opened_at = models.DateTimeField(auto_now_add=True)
	summary = models.TextField()
	requested_action = models.CharField(max_length=500, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)


class ComplaintDetermination(models.Model):
	class Finding(models.TextChoices):
		UPHELD = 'UPHELD', 'Complaint upheld'
		NOT_UPHELD = 'NOT_UPHELD', 'Complaint not upheld'
		PARTIALLY_UPHELD = 'PARTIALLY_UPHELD', 'Complaint partially upheld'
		ADMINISTRATIVE_REMEDY = 'ADMINISTRATIVE_REMEDY', 'Administrative remedy required'

	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='determinations')
	finding = models.CharField(max_length=28, choices=Finding.choices)
	remedy = models.TextField()
	determined_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='complaint_determinations')
	determined_at = models.DateTimeField(auto_now_add=True)
	approved_by = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='approved_complaint_determinations')


class ComplaintCommunication(models.Model):
	class Channel(models.TextChoices):
		PHONE = 'PHONE', 'Phone'
		EMAIL = 'EMAIL', 'Email'
		LETTER = 'LETTER', 'Letter'
		IN_PERSON = 'IN_PERSON', 'In person'

	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='communications')
	channel = models.CharField(max_length=16, choices=Channel.choices)
	recipient = models.CharField(max_length=180)
	outcome = models.CharField(max_length=500)
	communicated_at = models.DateTimeField()
	recorded_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='complaint_communications')
	supporting_document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.PROTECT, related_name='communication_records')


class ComplaintDocument(models.Model):
	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='document_links')
	document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='complaint_links')
	linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='linked_complaint_documents')
	linked_at = models.DateTimeField(auto_now_add=True)
	purpose = models.CharField(max_length=240)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['complaint', 'document'], name='unique_complaint_document_link')]


class ComplaintEvent(models.Model):
	class EventType(models.TextChoices):
		RECEIVED = 'RECEIVED', 'Complaint received'
		ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
		CLASSIFIED = 'CLASSIFIED', 'Classified'
		ASSIGNED = 'ASSIGNED', 'Assigned'
		REASSIGNED = 'REASSIGNED', 'Reassigned'
		INQUIRY_OPENED = 'INQUIRY_OPENED', 'Inquiry opened'
		DETERMINED = 'DETERMINED', 'Determination recorded'
		COMMUNICATED = 'COMMUNICATED', 'Outcome communicated'
		ESCALATED = 'ESCALATED', 'Escalated'
		WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
		REFERRED_OUT = 'REFERRED_OUT', 'Referred out'
		TYPE_A_HANDOFF = 'TYPE_A_HANDOFF', 'Transferred to conduct'
		COMMENT = 'COMMENT', 'Comment added'

	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='events')
	event_type = models.CharField(max_length=20, choices=EventType.choices)
	occurred_at = models.DateTimeField(auto_now_add=True)
	actor = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='complaint_events')
	actor_name = models.CharField(max_length=160, blank=True)
	detail = models.CharField(max_length=700)
	previous_status = models.CharField(max_length=24, blank=True)
	resulting_status = models.CharField(max_length=24, blank=True)
	automatic = models.BooleanField(default=False)

	class Meta:
		ordering = ['occurred_at', 'pk']

	def save(self, *args, **kwargs):
		if not self.pk and self.actor:
			self.actor_name = str(self.actor)
		super().save(*args, **kwargs)


class FileRecallOrder(models.Model):
	complaint = models.ForeignKey(Complaint, on_delete=models.PROTECT, related_name='recall_orders')
	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='recall_orders')
	issuer = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='issued_recall_orders')
	authority = models.CharField(max_length=240)
	issued_at = models.DateTimeField(auto_now_add=True)
	directive = models.TextField()
	target_custodian = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='received_recall_orders')
	response_due_at = models.DateTimeField()
	acknowledged_at = models.DateTimeField(null=True, blank=True)
