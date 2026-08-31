from django.db import models
from django.conf import settings
from common.models import Office, Region
from documents.models import Document
from staff.models import StaffProfile

class CaseReference(models.Model):
	class Stage(models.TextChoices):
		POLICE_OPENED = 'POLICE_OPENED', 'Police opened'
		POLICE_PREPARING = 'POLICE_PREPARING', 'Police preparing'
		DISPATCHED_TO_ODPP = 'DISPATCHED_TO_ODPP', 'Dispatched to ODPP'
		ODPP_RECEIVED = 'ODPP_RECEIVED', 'ODPP received'
		UNDER_PERUSAL = 'UNDER_PERUSAL', 'Under perusal'
		DFI_ISSUED = 'DFI_ISSUED', 'DFI issued'
		SANCTIONED = 'SANCTIONED', 'Sanctioned'
		BEFORE_COURT = 'BEFORE_COURT', 'Before court'
		HEARING = 'HEARING', 'Hearing / trial'
		JUDGEMENT_DELIVERED = 'JUDGEMENT_DELIVERED', 'Judgement delivered'
		CLOSED = 'CLOSED', 'Closed'

	class JudgementOutcome(models.TextChoices):
		CONVICTED = 'CONVICTED', 'Convicted'
		ACQUITTED = 'ACQUITTED', 'Acquitted'
		DISCHARGED = 'DISCHARGED', 'Discharged'
		WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
		OTHER = 'OTHER', 'Other'

	class Sensitivity(models.TextChoices):
		STANDARD = 'STANDARD', 'Standard'
		RESTRICTED = 'RESTRICTED', 'Restricted'
		CONFIDENTIAL = 'CONFIDENTIAL', 'Confidential'

	reference = models.CharField(max_length=40, unique=True)
	title = models.CharField(max_length=180)
	complaint_context = models.CharField(max_length=500)
	stage = models.CharField(max_length=24, choices=Stage.choices, default=Stage.POLICE_OPENED)
	judgement_outcome = models.CharField(max_length=16, choices=JudgementOutcome.choices, blank=True)
	sensitivity = models.CharField(max_length=16, choices=Sensitivity.choices, default=Sensitivity.STANDARD)
	originating_station = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='originated_cases')
	responsible_region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='cases')
	current_office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='held_cases')
	current_custodian = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='held_cases')
	allocated_to = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='allocated_cases')
	opened_on = models.DateField()
	expected_action_on = models.DateField(null=True, blank=True)
	last_meaningful_update_at = models.DateTimeField()
	is_demo = models.BooleanField(default=False)

	class Meta:
		ordering = ['-last_meaningful_update_at', 'reference']

	def __str__(self):
		return self.reference

class CaseIdentifier(models.Model):
	class ReferenceType(models.TextChoices):
		SD_OB = 'SD_OB', 'Station diary / occurrence book'
		CRB = 'CRB', 'Crime report book'
		ODPP = 'ODPP', 'ODPP reference'
		COURT = 'COURT', 'Court reference'

	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='identifiers')
	reference_type = models.CharField(max_length=12, choices=ReferenceType.choices)
	value = models.CharField(max_length=100)
	issuing_office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='issued_case_identifiers')
	issued_on = models.DateField(null=True, blank=True)
	is_verified = models.BooleanField(default=False)
	verified_by = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='verified_case_identifiers')

	class Meta:
		constraints = [models.UniqueConstraint(fields=['reference_type', 'value'], name='unique_case_identifier_value')]
		ordering = ['reference_type', 'value']

	def __str__(self):
		return f'{self.get_reference_type_display()}: {self.value}'

class CaseParty(models.Model):
	class Role(models.TextChoices):
		COMPLAINANT = 'COMPLAINANT', 'Victim / complainant'
		ACCUSED = 'ACCUSED', 'Accused / defendant'
		NEXT_OF_KIN = 'NEXT_OF_KIN', 'Next of kin'
		WITNESS = 'WITNESS', 'Witness / informant'
		COUNSEL = 'COUNSEL', 'Legal representative'

	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='parties')
	role = models.CharField(max_length=16, choices=Role.choices)
	full_name = models.CharField(max_length=160)
	nin = models.CharField(max_length=14, verbose_name='NIN')
	phone = models.CharField(max_length=32, blank=True)
	recorded_by = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='recorded_case_parties')
	recorded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['case_id', 'role', 'full_name']
		constraints = [models.UniqueConstraint(fields=['case', 'nin'], name='unique_case_party_nin')]

	def __str__(self):
		return f'{self.full_name} ({self.get_role_display()}) - {self.case.reference}'

class CaseMovement(models.Model):
	class MovementType(models.TextChoices):
		DISPATCH = 'DISPATCH', 'Dispatch'
		RECEIPT = 'RECEIPT', 'Receipt'
		INTERNAL_TRANSFER = 'INTERNAL_TRANSFER', 'Internal transfer'
		RETURN_FOR_ACTION = 'RETURN_FOR_ACTION', 'Return for action'
		COURT_TRANSFER = 'COURT_TRANSFER', 'Court transfer'
		ARCHIVAL = 'ARCHIVAL', 'Closure / archival'

	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='movements')
	movement_type = models.CharField(max_length=20, choices=MovementType.choices)
	sent_from = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='outgoing_case_movements')
	sent_to = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='incoming_case_movements')
	sent_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='sent_case_movements')
	received_by = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='received_case_movements')
	moved_at = models.DateTimeField()
	received_at = models.DateTimeField(null=True, blank=True)
	declared_contents = models.CharField(max_length=300)
	receipt_acknowledged = models.BooleanField(default=False)
	note = models.CharField(max_length=500, blank=True)
	corrects = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='corrections')

	class Meta:
		ordering = ['moved_at', 'pk']

	def __str__(self):
		return f'{self.case.reference} - {self.get_movement_type_display()}'

class CaseAssignment(models.Model):
	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='assignments')
	assignee = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='case_assignments')
	assigned_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='assigned_cases')
	assigned_at = models.DateTimeField(auto_now_add=True)
	ended_at = models.DateTimeField(null=True, blank=True)
	reason = models.CharField(max_length=300)
	priority = models.PositiveSmallIntegerField(default=3)

	class Meta:
		ordering = ['-assigned_at']

class CaseDocumentLink(models.Model):
	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='document_links')
	document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='case_links')
	linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='linked_case_documents')
	linked_at = models.DateTimeField(auto_now_add=True)
	purpose = models.CharField(max_length=240)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['case', 'document'], name='unique_case_document_link')]

class CaseComment(models.Model):
	case = models.ForeignKey(CaseReference, on_delete=models.PROTECT, related_name='comments')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='case_comments')
	author_name = models.CharField(max_length=160, editable=False)
	author_officer_number = models.CharField(max_length=50, blank=True, editable=False)
	author_role = models.CharField(max_length=32, blank=True, editable=False)
	body = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

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
		return f'Comment by {self.author_name} on {self.case.reference}'
