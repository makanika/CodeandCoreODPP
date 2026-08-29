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

CONDUCT_ROLES = {
    StaffProfile.Role.INTERNAL_AFFAIRS,
    StaffProfile.Role.DPP,
    StaffProfile.Role.DEPUTY_DPP,
}


def is_director(profile):
    """Whether this profile holds directorate-level authority to assign, move, and direct work across offices."""
    return profile.role in DIRECTOR_ROLES


def can_access_conduct(profile):
    """Whether this profile may see sealed Type A conduct material at all.

    Everyone else must get an outright 403, not a filtered empty list: conduct
    material must be absent from views and exports, not merely hidden.
    """
    return profile.role in CONDUCT_ROLES


def assignable_staff(requesting_profile):
    """Staff who can receive a delegated complaint or case.

    Excludes the requesting officer (delegation implies handing work to someone else) and
    apex oversight roles (the DPP and Deputy DPP direct work; they are not caseworkers).
    """
    return StaffProfile.objects.filter(is_active=True).exclude(pk=requesting_profile.pk).exclude(role__in=APEX_OVERSIGHT_ROLES)
