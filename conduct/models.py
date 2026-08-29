from django.db import models


class ConductComplaint(models.Model):
	"""A sealed Type A allegation against an officer. Lives entirely on the isolated
	'conduct' database — see core/db_routers.py. Every reference to a person or
	office on the primary database is stored as a plain id plus a name snapshot,
	never a ForeignKey: the router forbids cross-database relations, and a sealed
	record should reflect who someone was at the time, not track live edits."""

	class AllegationCategory(models.TextChoices):
		ABUSE_OF_OFFICE = 'ABUSE_OF_OFFICE', 'Abuse of office'
		BRIBERY_CORRUPTION = 'BRIBERY_CORRUPTION', 'Bribery or corruption'
		EVIDENCE_TAMPERING = 'EVIDENCE_TAMPERING', 'Evidence tampering'
		UNPROFESSIONAL_CONDUCT = 'UNPROFESSIONAL_CONDUCT', 'Unprofessional conduct'
		DELAY_OR_NEGLECT = 'DELAY_OR_NEGLECT', 'Delay or neglect of duty'
		HARASSMENT = 'HARASSMENT', 'Harassment or intimidation'
		OTHER = 'OTHER', 'Other misconduct'

	class Severity(models.TextChoices):
		LOW = 'LOW', 'Low'
		MEDIUM = 'MEDIUM', 'Medium'
		HIGH = 'HIGH', 'High'
		CRITICAL = 'CRITICAL', 'Critical'

	class Status(models.TextChoices):
		RECEIVED = 'RECEIVED', 'Received'
		UNDER_INQUIRY = 'UNDER_INQUIRY', 'Under inquiry'
		REFERRED_TO_DISCIPLINE = 'REFERRED_TO_DISCIPLINE', 'Referred to disciplinary process'
		SUBSTANTIATED = 'SUBSTANTIATED', 'Substantiated'
		NOT_SUBSTANTIATED = 'NOT_SUBSTANTIATED', 'Not substantiated'
		WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
		CLOSED = 'CLOSED', 'Closed'

	reference = models.CharField(max_length=32, unique=True, editable=False)
	source_complaint_reference = models.CharField(max_length=32, blank=True, help_text='The public complaint reference this was escalated from, if any.')

	subject_officer_id = models.PositiveIntegerField()
	subject_officer_name = models.CharField(max_length=160)
	subject_officer_number = models.CharField(max_length=50)
	subject_officer_role = models.CharField(max_length=32)
	subject_officer_office = models.CharField(max_length=160, blank=True)

	complainant_name = models.CharField(max_length=160)
	complainant_nin = models.CharField(max_length=14, blank=True)
	complainant_phone = models.CharField(max_length=32, blank=True)
	complainant_email = models.EmailField(blank=True)

	allegation_category = models.CharField(max_length=32, choices=AllegationCategory.choices)
	severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM)
	narrative = models.TextField()
	status = models.CharField(max_length=28, choices=Status.choices, default=Status.RECEIVED)

	assigned_investigator_id = models.PositiveIntegerField(null=True, blank=True)
	assigned_investigator_name = models.CharField(max_length=160, blank=True)

	received_at = models.DateTimeField(auto_now_add=True)
	last_meaningful_update_at = models.DateTimeField(auto_now_add=True)
	is_demo = models.BooleanField(default=False)

	class Meta:
		ordering = ['-last_meaningful_update_at', 'reference']

	def __str__(self):
		return self.reference


class ConductSequence(models.Model):
	year = models.PositiveSmallIntegerField(unique=True)
	next_value = models.PositiveIntegerField(default=1)


class ConductEvent(models.Model):
	class EventType(models.TextChoices):
		RECEIVED = 'RECEIVED', 'Received'
		ASSIGNED = 'ASSIGNED', 'Investigator assigned'
		REASSIGNED = 'REASSIGNED', 'Investigator reassigned'
		STATUS_CHANGED = 'STATUS_CHANGED', 'Status changed'
		COMMENT = 'COMMENT', 'Comment added'
		DETERMINATION = 'DETERMINATION', 'Determination recorded'

	conduct_complaint = models.ForeignKey(ConductComplaint, on_delete=models.PROTECT, related_name='events')
	event_type = models.CharField(max_length=20, choices=EventType.choices)
	actor_id = models.PositiveIntegerField(null=True, blank=True)
	actor_name = models.CharField(max_length=160, blank=True)
	detail = models.CharField(max_length=700)
	previous_status = models.CharField(max_length=28, blank=True)
	resulting_status = models.CharField(max_length=28, blank=True)
	occurred_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['occurred_at', 'pk']

	def __str__(self):
		return f'{self.conduct_complaint.reference} - {self.get_event_type_display()}'


class ConductDetermination(models.Model):
	class Finding(models.TextChoices):
		SUBSTANTIATED = 'SUBSTANTIATED', 'Substantiated'
		NOT_SUBSTANTIATED = 'NOT_SUBSTANTIATED', 'Not substantiated'
		PARTIALLY_SUBSTANTIATED = 'PARTIALLY_SUBSTANTIATED', 'Partially substantiated'
		INCONCLUSIVE = 'INCONCLUSIVE', 'Inconclusive'

	class RecommendedAction(models.TextChoices):
		NO_ACTION = 'NO_ACTION', 'No further action'
		REPRIMAND = 'REPRIMAND', 'Reprimand'
		SUSPENSION = 'SUSPENSION', 'Suspension'
		DISMISSAL = 'DISMISSAL', 'Dismissal'
		REFERRED_TO_PROSECUTION = 'REFERRED_TO_PROSECUTION', 'Referred for prosecution'
		OTHER = 'OTHER', 'Other'

	conduct_complaint = models.ForeignKey(ConductComplaint, on_delete=models.PROTECT, related_name='determinations')
	finding = models.CharField(max_length=28, choices=Finding.choices)
	recommended_action = models.CharField(max_length=28, choices=RecommendedAction.choices)
	notes = models.TextField(blank=True)
	determined_by_id = models.PositiveIntegerField()
	determined_by_name = models.CharField(max_length=160)
	determined_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-determined_at']

	def __str__(self):
		return f'{self.conduct_complaint.reference} - {self.get_finding_display()}'
