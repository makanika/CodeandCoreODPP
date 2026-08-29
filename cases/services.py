from django.db.models import Q

from staff.models import StaffProfile


NATIONAL_CASE_ROLES = {
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
    StaffProfile.Role.REGISTRY_OFFICER,
}


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