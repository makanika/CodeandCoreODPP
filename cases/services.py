from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from staff.models import StaffProfile


NATIONAL_CASE_ROLES = {
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
    StaffProfile.Role.REGISTRY_OFFICER,
}

# The order the complaint-context reference moves through: police station,
# through ODPP review, to court, and on to judgement. Advancing a stage only
# ever moves forward along this list; CLOSED is reachable from any point
# (a matter can be withdrawn or nolle prossed before judgement).
STAGE_ORDER = [
    'POLICE_OPENED',
    'POLICE_PREPARING',
    'DISPATCHED_TO_ODPP',
    'ODPP_RECEIVED',
    'UNDER_PERUSAL',
    'DFI_ISSUED',
    'SANCTIONED',
    'BEFORE_COURT',
    'HEARING',
    'JUDGEMENT_DELIVERED',
    'CLOSED',
]


def visible_cases_for(profile):
    """Return the complaint-context case records available to a staff profile."""
    from .models import CaseReference

    if profile.role in NATIONAL_CASE_ROLES:
        return CaseReference.objects.all()

    permitted_office_ids = profile.scope_assignments.filter(
        scope_level=profile.scope_assignments.model.ScopeLevel.OFFICE,
        assigned_until__isnull=True,
    ).values_list('office_id', flat=True)
    return CaseReference.objects.filter(
        Q(allocated_to=profile)
        | Q(current_custodian=profile)
        | Q(originating_station_id__in=permitted_office_ids)
        | Q(current_office_id__in=permitted_office_ids)
    ).distinct()


def assign_case(case, *, assignee, assigned_by, reason, priority=3):
    """End any open allocation and allocate the case to a new responsible staff member."""
    from .models import CaseAssignment

    with transaction.atomic():
        previous_assignment = case.assignments.filter(ended_at__isnull=True).first()
        now = timezone.now()
        if previous_assignment:
            previous_assignment.ended_at = now
            previous_assignment.save(update_fields=['ended_at'])
        CaseAssignment.objects.create(case=case, assignee=assignee, assigned_by=assigned_by, reason=reason, priority=priority)
        case.allocated_to = assignee
        case.last_meaningful_update_at = now
        case.save(update_fields=['allocated_to', 'last_meaningful_update_at'])
    return case


def move_case(case, *, movement_type, sent_to, sent_by, declared_contents, received_by=None, note='', acknowledge_receipt=True):
    """Record a case movement and, once receipt is acknowledged, update the case's current custody."""
    from .models import CaseMovement

    with transaction.atomic():
        now = timezone.now()
        movement = CaseMovement.objects.create(
            case=case,
            movement_type=movement_type,
            sent_from=case.current_office,
            sent_to=sent_to,
            sent_by=sent_by,
            received_by=received_by if acknowledge_receipt else None,
            moved_at=now,
            received_at=now if acknowledge_receipt else None,
            declared_contents=declared_contents,
            receipt_acknowledged=acknowledge_receipt,
            note=note,
        )
        if acknowledge_receipt:
            case.current_office = sent_to
            if received_by:
                case.current_custodian = received_by
            case.last_meaningful_update_at = now
            case.save(update_fields=['current_office', 'current_custodian', 'last_meaningful_update_at'])
    return movement


def add_case_comment(case, *, author, body):
    from .models import CaseComment

    return CaseComment.objects.create(case=case, author=author, body=body)


def advance_case_stage(case, *, new_stage, actor, note='', judgement_outcome=''):
    """Move the case reference forward through the police-to-judgement pipeline and log the change."""
    from .models import CaseComment, CaseReference

    if new_stage == case.stage:
        raise ValueError('The case is already at this stage.')
    if new_stage != CaseReference.Stage.CLOSED:
        if STAGE_ORDER.index(new_stage) < STAGE_ORDER.index(case.stage):
            raise ValueError('A case stage cannot move backward through the pipeline.')
    if new_stage == CaseReference.Stage.JUDGEMENT_DELIVERED and not judgement_outcome:
        raise ValueError('Record the judgement outcome when marking judgement as delivered.')

    with transaction.atomic():
        case.stage = new_stage
        update_fields = ['stage', 'last_meaningful_update_at']
        if judgement_outcome:
            case.judgement_outcome = judgement_outcome
            update_fields.append('judgement_outcome')
        case.last_meaningful_update_at = timezone.now()
        case.save(update_fields=update_fields)
        detail = f'Case stage advanced to {case.get_stage_display()}.'
        if judgement_outcome:
            detail += f' Judgement outcome: {case.get_judgement_outcome_display()}.'
        if note:
            detail += f' {note}'
        CaseComment.objects.create(case=case, author=actor, body=detail)
    return case