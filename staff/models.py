from django.conf import settings
from django.db import models

from common.models import Office


class StaffProfile(models.Model):
    class Organisation(models.TextChoices):
        ODPP = 'ODPP', 'Office of the Director of Public Prosecutions'
        UGANDA_POLICE = 'UGANDA_POLICE', 'Uganda Police Force'

    class Role(models.TextChoices):
        INVESTIGATING_OFFICER = 'INVESTIGATING_OFFICER', 'Investigating Officer'
        STATION_SUPERVISOR = 'STATION_SUPERVISOR', 'Station Supervisor'
        POLICE_LIAISON = 'POLICE_LIAISON', 'Police Liaison'
        REGISTRY_CLERK = 'REGISTRY_CLERK', 'Registry Clerk'
        REGISTRY_OFFICER = 'REGISTRY_OFFICER', 'Registry Officer'
        RESIDENT_STATE_ATTORNEY = 'RESIDENT_STATE_ATTORNEY', 'Resident State Attorney'
        REGIONAL_INSPECTORATE = 'REGIONAL_INSPECTORATE', 'Regional Inspectorate Officer'
        HEAD_OF_COMPLAINTS = 'HEAD_OF_COMPLAINTS', 'Head of Complaints'
        INTERNAL_AFFAIRS = 'INTERNAL_AFFAIRS', 'Internal Affairs Officer'
        DPP = 'DPP', 'Director of Public Prosecutions'
        DEPUTY_DPP = 'DEPUTY_DPP', 'Deputy Director of Public Prosecutions'
        DIRECTORATE_HEAD = 'DIRECTORATE_HEAD', 'Directorate Head'

    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='staff_profile')
    officer_number = models.CharField(max_length=50, unique=True)
    organisation = models.CharField(max_length=24, choices=Organisation.choices)
    role = models.CharField(max_length=32, choices=Role.choices)
    work_phone = models.CharField(max_length=32, blank=True)
    job_title = models.CharField(max_length=120)
    rank = models.CharField(max_length=80, blank=True)
    current_office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.PROTECT, related_name='current_staff')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['account__last_name', 'account__first_name', 'officer_number']

    def __str__(self):
        return self.account.get_full_name() or self.officer_number


class StaffPosting(models.Model):
    staff_member = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='postings')
    office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name='staff_postings')
    reports_to = models.ForeignKey(StaffProfile, null=True, blank=True, on_delete=models.PROTECT, related_name='direct_reports')
    job_title = models.CharField(max_length=120)
    rank = models.CharField(max_length=80, blank=True)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='recorded_postings')
    reason = models.CharField(max_length=240)

    class Meta:
        ordering = ['-effective_from', 'staff_member__officer_number']

    def __str__(self):
        return f'{self.staff_member} - {self.office}'


class StaffScopeAssignment(models.Model):
    class ScopeLevel(models.TextChoices):
        NATIONAL = 'NATIONAL', 'National'
        REGION = 'REGION', 'Region'
        OFFICE = 'OFFICE', 'Office'

    staff_member = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name='scope_assignments')
    scope_level = models.CharField(max_length=16, choices=ScopeLevel.choices)
    office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.PROTECT, related_name='scope_assignments')
    assigned_from = models.DateField()
    assigned_until = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assigned_staff_scopes')
    reason = models.CharField(max_length=240)

    class Meta:
        ordering = ['-assigned_from', 'staff_member__officer_number']