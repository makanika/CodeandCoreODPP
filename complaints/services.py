from io import BytesIO
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from staff.models import StaffProfile

from .models import Complaint, ComplaintAssignment, ComplaintEvent, ComplaintSequence


TYPE_B_TRANSITIONS = {
    Complaint.Status.RECEIVED: {Complaint.Status.OPEN_RSA, Complaint.Status.WITHDRAWN, Complaint.Status.REFERRED_OUT},
    Complaint.Status.OPEN_RSA: {Complaint.Status.RESOLVED_RSA, Complaint.Status.ESCALATED_REGIONAL, Complaint.Status.WITHDRAWN, Complaint.Status.REFERRED_OUT},
    Complaint.Status.RESOLVED_RSA: set(),
    Complaint.Status.ESCALATED_REGIONAL: {Complaint.Status.RESOLVED_REGIONAL, Complaint.Status.ESCALATED_HQ, Complaint.Status.WITHDRAWN, Complaint.Status.REFERRED_OUT},
    Complaint.Status.RESOLVED_REGIONAL: set(),
    Complaint.Status.ESCALATED_HQ: {Complaint.Status.REINSTATED, Complaint.Status.SANCTIONED, Complaint.Status.WITHDRAWN, Complaint.Status.REFERRED_OUT},
    Complaint.Status.REINSTATED: set(),
    Complaint.Status.SANCTIONED: set(),
    Complaint.Status.WITHDRAWN: set(),
    Complaint.Status.REFERRED_OUT: set(),
}

NATIONAL_COMPLAINT_ROLES = {
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
    StaffProfile.Role.HEAD_OF_COMPLAINTS,
    StaffProfile.Role.REGISTRY_OFFICER,
}


def visible_complaints_for(profile):
    """Return non-conduct complaints permitted to the supplied staff profile."""
    queryset = Complaint.objects.exclude(classification=Complaint.Classification.TYPE_A_HANDOFF)
    if profile.role in NATIONAL_COMPLAINT_ROLES:
        return queryset
    if profile.role == StaffProfile.Role.INTERNAL_AFFAIRS:
        return queryset.none()

    office_ids = profile.scope_assignments.filter(
        scope_level=profile.scope_assignments.model.ScopeLevel.OFFICE,
        assigned_until__isnull=True,
    ).values_list('office_id', flat=True)
    region_ids = profile.scope_assignments.filter(
        scope_level=profile.scope_assignments.model.ScopeLevel.REGION,
        assigned_until__isnull=True,
        office__region__isnull=False,
    ).values_list('office__region_id', flat=True)
    if profile.current_office and profile.current_office.region_id:
        region_ids = list(region_ids) + [profile.current_office.region_id]

    filters = Q(assigned_to=profile) | Q(assigned_office_id__in=office_ids)
    if profile.role == StaffProfile.Role.REGIONAL_INSPECTORATE:
        filters |= Q(related_case__responsible_region_id__in=region_ids)
    return queryset.filter(filters).distinct()


def create_complaint(*, intake_channel, complainant_name, subject, narrative, related_case=None, supplied_case_reference='', complainant_nin='', complainant_phone='', complainant_email='', preferred_contact_channel='', captured_by=None, source_evidence_reference='', is_demo=False):
    now = timezone.now()
    with transaction.atomic():
        sequence, _ = ComplaintSequence.objects.select_for_update().get_or_create(year=now.year)
        reference = f'CMP/{now.year}/{sequence.next_value:06d}'
        sequence.next_value += 1
        sequence.save(update_fields=['next_value'])
        pin = f'{secrets.randbelow(1_000_000):06d}'
        complaint = Complaint.objects.create(
            reference=reference,
            tracking_pin_hash=make_password(pin),
            intake_channel=intake_channel,
            captured_by=captured_by,
            source_evidence_reference=source_evidence_reference,
            complainant_name=complainant_name,
            complainant_nin=complainant_nin,
            complainant_phone=complainant_phone,
            complainant_email=complainant_email,
            preferred_contact_channel=preferred_contact_channel,
            related_case=related_case,
            supplied_case_reference=supplied_case_reference,
            subject=subject,
            narrative=narrative,
            is_demo=is_demo,
        )
        ComplaintEvent.objects.create(
            complaint=complaint,
            event_type=ComplaintEvent.EventType.RECEIVED,
            actor=getattr(captured_by, 'staff_profile', None),
            detail='Complaint received through the declared intake channel.',
            resulting_status=Complaint.Status.RECEIVED,
        )
    complaint.receipt_pin = pin
    return complaint


def verify_tracking_credentials(reference, pin):
    try:
        complaint = Complaint.objects.get(reference=reference)
    except Complaint.DoesNotExist:
        return None
    return complaint if check_password(pin, complaint.tracking_pin_hash) else None


def qr_locator_payload(complaint):
    return signing.dumps({'locator': str(complaint.qr_locator_id)}, salt='complaints.receipt-locator', compress=True)


def qr_png(complaint):
    import qrcode

    image = qrcode.make(qr_locator_payload(complaint))
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def classify_type_b(complaint, actor):
    complaint.classification = Complaint.Classification.TYPE_B
    complaint.save(update_fields=['classification'])
    ComplaintEvent.objects.create(
        complaint=complaint,
        event_type=ComplaintEvent.EventType.CLASSIFIED,
        actor=actor,
        detail='Classified as a Type B process complaint.',
        previous_status=complaint.status,
        resulting_status=complaint.status,
    )


def handoff_type_a(complaint, *, actor, conduct_reference):
    """Record a completed conduct handoff without retaining sealed allegation content."""
    if not conduct_reference:
        raise ValueError('A sealed conduct reference is required before Type A handoff.')
    complaint.classification = Complaint.Classification.TYPE_A_HANDOFF
    complaint.status = Complaint.Status.TYPE_A_HANDOFF
    complaint.type_a_handoff_reference = conduct_reference
    complaint.subject = 'Confidential conduct complaint'
    complaint.narrative = ''
    complaint.public_status = 'Your complaint has been received and is being handled through the appropriate process.'
    complaint.last_meaningful_update_at = timezone.now()
    complaint.save(
        update_fields=[
            'classification',
            'status',
            'type_a_handoff_reference',
            'subject',
            'narrative',
            'public_status',
            'last_meaningful_update_at',
        ],
    )
    ComplaintEvent.objects.create(
        complaint=complaint,
        event_type=ComplaintEvent.EventType.TYPE_A_HANDOFF,
        actor=actor,
        detail='Classified and transferred to the sealed conduct workflow.',
        resulting_status=Complaint.Status.TYPE_A_HANDOFF,
    )


def transition_type_b(complaint, *, resulting_status, actor=None, detail, automatic=False):
    if complaint.classification != Complaint.Classification.TYPE_B:
        raise ValueError('Only Type B complaints can use the ordinary workflow.')
    if resulting_status not in TYPE_B_TRANSITIONS.get(complaint.status, set()):
        raise ValueError(f'Cannot transition from {complaint.status} to {resulting_status}.')
    previous_status = complaint.status
    complaint.status = resulting_status
    complaint.last_meaningful_update_at = timezone.now()
    complaint.save(update_fields=['status', 'last_meaningful_update_at'])
    ComplaintEvent.objects.create(
        complaint=complaint,
        event_type=ComplaintEvent.EventType.ESCALATED if resulting_status.startswith('ESCALATED') else ComplaintEvent.EventType.DETERMINED,
        actor=actor,
        detail=detail,
        previous_status=previous_status,
        resulting_status=resulting_status,
        automatic=automatic,
    )


def add_complaint_comment(complaint, *, actor, detail):
    return ComplaintEvent.objects.create(
        complaint=complaint,
        event_type=ComplaintEvent.EventType.COMMENT,
        actor=actor,
        detail=detail,
        previous_status=complaint.status,
        resulting_status=complaint.status,
    )


def assign_complaint(complaint, *, assignee, assigned_by, reason, due_at=None, priority=None):
    if complaint.classification != Complaint.Classification.TYPE_B:
        raise ValueError('Only Type B complaints can be assigned through the ordinary workflow.')
    previous_assignment = complaint.assignments.filter(ended_at__isnull=True).first()
    now = timezone.now()
    if previous_assignment:
        previous_assignment.ended_at = now
        previous_assignment.save(update_fields=['ended_at'])
    priority = priority or complaint.priority
    ComplaintAssignment.objects.create(complaint=complaint, assigned_to=assignee, assigned_by=assigned_by, reason=reason, priority=priority, due_at=due_at)
    complaint.assigned_to = assignee
    complaint.assigned_office = assignee.current_office
    complaint.priority = priority
    complaint.sla_due_at = due_at
    complaint.save(update_fields=['assigned_to', 'assigned_office', 'priority', 'sla_due_at'])
    ComplaintEvent.objects.create(
        complaint=complaint,
        event_type=ComplaintEvent.EventType.REASSIGNED if previous_assignment else ComplaintEvent.EventType.ASSIGNED,
        actor=assigned_by,
        detail=reason,
        previous_status=complaint.status,
        resulting_status=complaint.status,
    )