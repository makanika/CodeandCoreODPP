from django.db import transaction
from django.utils import timezone


STATUS_TRANSITIONS = {
    'RECEIVED': {'UNDER_INQUIRY', 'WITHDRAWN'},
    'UNDER_INQUIRY': {'SUBSTANTIATED', 'NOT_SUBSTANTIATED', 'REFERRED_TO_DISCIPLINE', 'WITHDRAWN'},
    'REFERRED_TO_DISCIPLINE': {'SUBSTANTIATED', 'NOT_SUBSTANTIATED', 'CLOSED'},
    'SUBSTANTIATED': {'CLOSED'},
    'NOT_SUBSTANTIATED': {'CLOSED'},
    'WITHDRAWN': {'CLOSED'},
    'CLOSED': set(),
}

FINDING_TO_STATUS = {
    'SUBSTANTIATED': 'SUBSTANTIATED',
    'NOT_SUBSTANTIATED': 'NOT_SUBSTANTIATED',
    'PARTIALLY_SUBSTANTIATED': 'SUBSTANTIATED',
    'INCONCLUSIVE': 'UNDER_INQUIRY',
}


def visible_conduct_for(profile):
    """Return the sealed conduct queryset a staff profile may see. Everyone outside
    CONDUCT_ROLES gets an empty queryset here, but the view itself must still refuse
    the request outright rather than rely on this filter alone."""
    from staff.permissions import can_access_conduct
    from .models import ConductComplaint

    if can_access_conduct(profile):
        return ConductComplaint.objects.all()
    return ConductComplaint.objects.none()


def receive_type_a_handoff(*, subject_officer, complainant_name, allegation_category, severity, narrative, actor, complainant_nin='', complainant_phone='', complainant_email='', source_complaint_reference=''):
    """Create the sealed conduct record. Called before complaints.services.handoff_type_a,
    which then redacts the originating public complaint using the reference this returns."""
    from .models import ConductComplaint, ConductEvent, ConductSequence

    now = timezone.now()
    with transaction.atomic(using='conduct'):
        sequence, _ = ConductSequence.objects.select_for_update().get_or_create(year=now.year)
        reference = f'CDT/{now.year}/{sequence.next_value:06d}'
        sequence.next_value += 1
        sequence.save(update_fields=['next_value'])
        conduct_complaint = ConductComplaint.objects.create(
            reference=reference,
            source_complaint_reference=source_complaint_reference,
            subject_officer_id=subject_officer.pk,
            subject_officer_name=str(subject_officer),
            subject_officer_number=subject_officer.officer_number,
            subject_officer_role=subject_officer.role,
            subject_officer_office=str(subject_officer.current_office or ''),
            complainant_name=complainant_name,
            complainant_nin=complainant_nin,
            complainant_phone=complainant_phone,
            complainant_email=complainant_email,
            allegation_category=allegation_category,
            severity=severity,
            narrative=narrative,
        )
        ConductEvent.objects.create(
            conduct_complaint=conduct_complaint,
            event_type=ConductEvent.EventType.RECEIVED,
            actor_id=actor.pk,
            actor_name=str(actor),
            detail='Received into the sealed conduct workflow.',
            resulting_status=ConductComplaint.Status.RECEIVED,
        )
    return conduct_complaint


def assign_investigator(conduct_complaint, *, investigator, actor):
    from .models import ConductEvent

    with transaction.atomic(using='conduct'):
        was_assigned = bool(conduct_complaint.assigned_investigator_id)
        conduct_complaint.assigned_investigator_id = investigator.pk
        conduct_complaint.assigned_investigator_name = str(investigator)
        conduct_complaint.last_meaningful_update_at = timezone.now()
        conduct_complaint.save(update_fields=['assigned_investigator_id', 'assigned_investigator_name', 'last_meaningful_update_at'])
        ConductEvent.objects.create(
            conduct_complaint=conduct_complaint,
            event_type=ConductEvent.EventType.REASSIGNED if was_assigned else ConductEvent.EventType.ASSIGNED,
            actor_id=actor.pk,
            actor_name=str(actor),
            detail=f'Assigned to {investigator}.',
        )
    return conduct_complaint


def change_status(conduct_complaint, *, new_status, actor, note=''):
    from .models import ConductEvent

    if new_status not in STATUS_TRANSITIONS.get(conduct_complaint.status, set()):
        raise ValueError(f'Cannot move a conduct record from {conduct_complaint.get_status_display()} to {dict(conduct_complaint.Status.choices)[new_status]}.')

    with transaction.atomic(using='conduct'):
        previous_status = conduct_complaint.status
        conduct_complaint.status = new_status
        conduct_complaint.last_meaningful_update_at = timezone.now()
        conduct_complaint.save(update_fields=['status', 'last_meaningful_update_at'])
        detail = f'Status changed to {conduct_complaint.get_status_display()}.'
        if note:
            detail += f' {note}'
        ConductEvent.objects.create(
            conduct_complaint=conduct_complaint,
            event_type=ConductEvent.EventType.STATUS_CHANGED,
            actor_id=actor.pk,
            actor_name=str(actor),
            detail=detail,
            previous_status=previous_status,
            resulting_status=new_status,
        )
    return conduct_complaint


def add_conduct_comment(conduct_complaint, *, actor, body):
    from .models import ConductEvent

    return ConductEvent.objects.create(
        conduct_complaint=conduct_complaint,
        event_type=ConductEvent.EventType.COMMENT,
        actor_id=actor.pk,
        actor_name=str(actor),
        detail=body,
    )


def record_determination(conduct_complaint, *, finding, recommended_action, notes, determined_by):
    from .models import ConductDetermination, ConductEvent

    with transaction.atomic(using='conduct'):
        determination = ConductDetermination.objects.create(
            conduct_complaint=conduct_complaint,
            finding=finding,
            recommended_action=recommended_action,
            notes=notes,
            determined_by_id=determined_by.pk,
            determined_by_name=str(determined_by),
        )
        ConductEvent.objects.create(
            conduct_complaint=conduct_complaint,
            event_type=ConductEvent.EventType.DETERMINATION,
            actor_id=determined_by.pk,
            actor_name=str(determined_by),
            detail=f'Determination recorded: {determination.get_finding_display()}. Recommended: {determination.get_recommended_action_display()}.',
        )
        new_status = FINDING_TO_STATUS.get(finding)
        if new_status and new_status in STATUS_TRANSITIONS.get(conduct_complaint.status, set()):
            change_status(conduct_complaint, new_status=new_status, actor=determined_by, note='Recorded via determination.')
    return determination
