from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from common.models import Office, Region
from staff.models import StaffPosting, StaffProfile, StaffScopeAssignment


DEMO_START_DATE = date(2026, 8, 29)
DEFAULT_PASSWORD = 'DEMO-Change-Me-2026!'


class Command(BaseCommand):
    help = 'Create or update fictional DEMO staff accounts, profiles, postings, and scopes.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Password for newly created DEMO accounts.')
        parser.add_argument('--reset-passwords', action='store_true', help='Reset every DEMO account password.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('DEMO staff can only be seeded while DJANGO_DEBUG is enabled.')

        offices = self._seed_offices()
        profiles = self._seed_profiles(offices, options['password'], options['reset_passwords'])
        self._seed_postings_and_scopes(profiles, offices)
        self.stdout.write(self.style.SUCCESS(f'Created or updated {len(profiles)} DEMO staff profiles.'))
        self.stdout.write('DEMO accounts use the supplied password only in this local development environment.')

    def _seed_offices(self):
        hq, _ = Office.objects.update_or_create(
            code='DEMO-HQ',
            defaults={'name': 'DEMO ODPP Headquarters', 'office_type': Office.OfficeType.HEADQUARTERS},
        )
        regions = {}
        regional_offices = {}
        for code, name in (
            ('DEMO-NAK', 'DEMO Nakawa Region'),
            ('DEMO-MAS', 'DEMO Masaka Region'),
            ('DEMO-ARU', 'DEMO Arua Region'),
        ):
            region, _ = Region.objects.update_or_create(code=code, defaults={'name': name})
            regions[code] = region
            regional_office, _ = Office.objects.update_or_create(
                code=f'{code}-ODPP',
                defaults={
                    'name': f'{name} ODPP Office',
                    'office_type': Office.OfficeType.REGIONAL_DPP,
                    'region': region,
                    'parent': hq,
                },
            )
            regional_offices[code] = regional_office

        offices = {'hq': hq, 'nakawa': regional_offices['DEMO-NAK'], 'masaka': regional_offices['DEMO-MAS'], 'arua': regional_offices['DEMO-ARU']}
        for key, code, name, region_code in (
            ('jinja_station', 'DEMO-JINJA-PS', 'DEMO Jinja Road Police Station', 'DEMO-NAK'),
            ('masaka_station', 'DEMO-MASAKA-CPS', 'DEMO Masaka Central Police Station', 'DEMO-MAS'),
            ('arua_station', 'DEMO-ARUA-CPS', 'DEMO Arua Central Police Station', 'DEMO-ARU'),
        ):
            office, _ = Office.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'office_type': Office.OfficeType.POLICE_STATION,
                    'region': regions[region_code],
                    'parent': regional_offices[region_code],
                },
            )
            offices[key] = office
        for key, code, region_code in (
            ('nakawa_registry', 'DEMO-NAK-REG', 'DEMO-NAK'),
            ('masaka_registry', 'DEMO-MAS-REG', 'DEMO-MAS'),
            ('arua_registry', 'DEMO-ARU-REG', 'DEMO-ARU'),
        ):
            office, _ = Office.objects.update_or_create(
                code=code,
                defaults={
                    'name': f'{regions[region_code].name} Registry',
                    'office_type': Office.OfficeType.REGISTRY,
                    'region': regions[region_code],
                    'parent': regional_offices[region_code],
                },
            )
            offices[key] = office
        return offices

    def _seed_profiles(self, offices, password, reset_passwords):
        Account = get_user_model()
        profiles = {}
        people = (
            ('dpp', 'demo.dpp', 'Diana', 'Nabirye', 'DEMO-ODPP-001', StaffProfile.Organisation.ODPP, StaffProfile.Role.DPP, 'Director of Public Prosecutions', '', 'hq'),
            ('deputy', 'demo.deputy', 'Moses', 'Okello', 'DEMO-ODPP-002', StaffProfile.Organisation.ODPP, StaffProfile.Role.DEPUTY_DPP, 'Deputy Director of Public Prosecutions', '', 'hq'),
            ('director', 'demo.director', 'Grace', 'Atwine', 'DEMO-ODPP-003', StaffProfile.Organisation.ODPP, StaffProfile.Role.DIRECTORATE_HEAD, 'Directorate Head, Inspections and Quality Assurance', '', 'hq'),
            ('complaints_head', 'demo.complaints', 'Sarah', 'Nakato', 'DEMO-ODPP-004', StaffProfile.Organisation.ODPP, StaffProfile.Role.HEAD_OF_COMPLAINTS, 'Head of Complaints', '', 'hq'),
            ('internal_affairs', 'demo.internal.affairs', 'Peter', 'Mugisha', 'DEMO-ODPP-005', StaffProfile.Organisation.ODPP, StaffProfile.Role.INTERNAL_AFFAIRS, 'Internal Affairs Officer', '', 'hq'),
            ('registry_officer', 'demo.registry.hq', 'Juliet', 'Aciro', 'DEMO-ODPP-006', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGISTRY_OFFICER, 'National Registry Officer', '', 'hq'),
            ('rsa', 'demo.rsa.arua', 'Amina', 'Kato', 'DEMO-ODPP-014', StaffProfile.Organisation.ODPP, StaffProfile.Role.RESIDENT_STATE_ATTORNEY, 'Resident State Attorney', '', 'arua'),
            ('inspector', 'demo.inspector.arua', 'Ronald', 'Ocen', 'DEMO-ODPP-015', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGIONAL_INSPECTORATE, 'Regional Inspectorate Officer', '', 'arua'),
            ('registry_clerk', 'demo.registry.arua', 'Mary', 'Akello', 'DEMO-ODPP-016', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGISTRY_CLERK, 'Registry Clerk', '', 'arua_registry'),
            ('station_supervisor', 'demo.oc.jinja', 'James', 'Okot', 'DEMO-UPF-001', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.STATION_SUPERVISOR, 'Officer Commanding Station', 'ASP', 'jinja_station'),
            ('investigating_officer', 'demo.io.jinja', 'Noah', 'Ssemakula', 'DEMO-UPF-002', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.INVESTIGATING_OFFICER, 'Investigating Officer', 'IP', 'jinja_station'),
            ('police_liaison', 'demo.liaison.masaka', 'Esther', 'Nansubuga', 'DEMO-UPF-003', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.POLICE_LIAISON, 'Police Liaison Officer', 'IP', 'masaka_station'),
        )
        for key, username, first_name, last_name, officer_number, organisation, role, title, rank, office_key in people:
            account, created = Account.objects.update_or_create(
                username=username,
                defaults={'first_name': first_name, 'last_name': last_name, 'email': f'{username}@demo.odpp.local', 'is_active': True},
            )
            if created or reset_passwords:
                account.set_password(password)
                account.save(update_fields=['password'])
            profile, _ = StaffProfile.objects.update_or_create(
                account=account,
                defaults={
                    'officer_number': officer_number,
                    'organisation': organisation,
                    'role': role,
                    'job_title': title,
                    'rank': rank,
                    'current_office': offices[office_key],
                    'is_active': True,
                },
            )
            profiles[key] = profile
        return profiles

    def _seed_postings_and_scopes(self, profiles, offices):
        supervisors = {
            'dpp': None,
            'deputy': 'dpp',
            'director': 'deputy',
            'complaints_head': 'director',
            'internal_affairs': 'director',
            'registry_officer': 'director',
            'rsa': 'director',
            'inspector': 'director',
            'registry_clerk': 'rsa',
            'station_supervisor': None,
            'investigating_officer': 'station_supervisor',
            'police_liaison': 'station_supervisor',
        }
        dpp_account = profiles['dpp'].account
        for key, profile in profiles.items():
            manager_key = supervisors[key]
            manager = profiles[manager_key] if manager_key else None
            StaffPosting.objects.update_or_create(
                staff_member=profile,
                is_primary=True,
                defaults={
                    'office': profile.current_office,
                    'reports_to': manager,
                    'job_title': profile.job_title,
                    'rank': profile.rank,
                    'effective_from': DEMO_START_DATE,
                    'effective_until': None,
                    'recorded_by': dpp_account,
                    'reason': 'DEMO initial operational posting',
                },
            )
            scope_level = StaffScopeAssignment.ScopeLevel.NATIONAL if key in {'dpp', 'deputy', 'director', 'complaints_head', 'internal_affairs', 'registry_officer'} else StaffScopeAssignment.ScopeLevel.OFFICE
            scope_office = None if scope_level == StaffScopeAssignment.ScopeLevel.NATIONAL else profile.current_office
            StaffScopeAssignment.objects.update_or_create(
                staff_member=profile,
                scope_level=scope_level,
                office=scope_office,
                defaults={
                    'assigned_from': DEMO_START_DATE,
                    'assigned_until': None,
                    'assigned_by': dpp_account,
                    'reason': 'DEMO initial access assignment',
                },
            )