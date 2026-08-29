from .models import StaffProfile

DIRECTOR_ROLES = {
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
    StaffProfile.Role.HEAD_OF_COMPLAINTS,
}

APEX_OVERSIGHT_ROLES = {
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
}


def is_director(profile):
    """Whether this profile holds directorate-level authority to assign, move, and direct work across offices."""
    return profile.role in DIRECTOR_ROLES


def assignable_staff(requesting_profile):
    """Staff who can receive a delegated complaint or case.

    Excludes the requesting officer (delegation implies handing work to someone else) and
    apex oversight roles (the DPP and Deputy DPP direct work; they are not caseworkers).
    """
    return StaffProfile.objects.filter(is_active=True).exclude(pk=requesting_profile.pk).exclude(role__in=APEX_OVERSIGHT_ROLES)
