from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from common.models import Office, Region
from staff.models import StaffPosting, StaffProfile, StaffScopeAssignment


SEED_START_DATE = date(2026, 8, 29)
DEFAULT_PASSWORD = 'ChangeMe-2026!'


class Command(BaseCommand):
    help = 'Create or update seed staff accounts, profiles, postings, and scopes for the pilot environment.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Password for newly created seed accounts.')
        parser.add_argument('--reset-passwords', action='store_true', help='Reset every seed account password.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Seed staff can only be created while DJANGO_DEBUG is enabled.')

        offices = self._seed_offices()
        profiles = self._seed_profiles(offices, options['password'], options['reset_passwords'])
        self._seed_postings_and_scopes(profiles, offices)
        self.stdout.write(self.style.SUCCESS(f'Created or updated {len(profiles)} staff profiles.'))
        self.stdout.write('Seed accounts use the supplied password only in this local development environment.')

    def _seed_offices(self):
        hq, _ = Office.objects.update_or_create(
            code='ODPP-HQ',
            defaults={'name': 'ODPP Headquarters', 'office_type': Office.OfficeType.HEADQUARTERS},
        )
        regions = {}
        regional_offices = {}
        for code, name in (
            ('NAK', 'Nakawa Region'),
            ('MAS', 'Masaka Region'),
            ('ARU', 'Arua Region'),
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

        offices = {'hq': hq, 'nakawa': regional_offices['NAK'], 'masaka': regional_offices['MAS'], 'arua': regional_offices['ARU']}
        for key, code, name, region_code in (
            ('jinja_station', 'JINJA-PS', 'Jinja Road Police Station', 'NAK'),
            ('masaka_station', 'MASAKA-CPS', 'Masaka Central Police Station', 'MAS'),
            ('arua_station', 'ARUA-CPS', 'Arua Central Police Station', 'ARU'),
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
            ('nakawa_registry', 'NAK-REG', 'NAK'),
            ('masaka_registry', 'MAS-REG', 'MAS'),
            ('arua_registry', 'ARU-REG', 'ARU'),
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
            ('dpp', 'linus.anguzu@odpp.local', 'Linus', 'Anguzu', 'ODPP-001', StaffProfile.Organisation.ODPP, StaffProfile.Role.DPP, 'Director of Public Prosecutions', '', 'hq'),
            ('deputy', 'moses.okello@odpp.local', 'Moses', 'Okello', 'ODPP-002', StaffProfile.Organisation.ODPP, StaffProfile.Role.DEPUTY_DPP, 'Deputy Director of Public Prosecutions', '', 'hq'),
            ('director', 'grace.atwine@odpp.local', 'Grace', 'Atwine', 'ODPP-003', StaffProfile.Organisation.ODPP, StaffProfile.Role.DIRECTORATE_HEAD, 'Directorate Head, Inspections and Quality Assurance', '', 'hq'),
            ('complaints_head', 'sarah.nakato@odpp.local', 'Sarah', 'Nakato', 'ODPP-004', StaffProfile.Organisation.ODPP, StaffProfile.Role.HEAD_OF_COMPLAINTS, 'Head of Complaints', '', 'hq'),
            ('internal_affairs', 'peter.mugisha@odpp.local', 'Peter', 'Mugisha', 'ODPP-005', StaffProfile.Organisation.ODPP, StaffProfile.Role.INTERNAL_AFFAIRS, 'Internal Affairs Officer', '', 'hq'),
            ('registry_officer', 'juliet.aciro@odpp.local', 'Juliet', 'Aciro', 'ODPP-006', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGISTRY_OFFICER, 'National Registry Officer', '', 'hq'),
            ('rsa', 'amina.kato@odpp.local', 'Amina', 'Kato', 'ODPP-014', StaffProfile.Organisation.ODPP, StaffProfile.Role.RESIDENT_STATE_ATTORNEY, 'Resident State Attorney', '', 'arua'),
            ('inspector', 'ronald.ocen@odpp.local', 'Ronald', 'Ocen', 'ODPP-015', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGIONAL_INSPECTORATE, 'Regional Inspectorate Officer', '', 'arua'),
            ('registry_clerk', 'mary.akello@odpp.local', 'Mary', 'Akello', 'ODPP-016', StaffProfile.Organisation.ODPP, StaffProfile.Role.REGISTRY_CLERK, 'Registry Clerk', '', 'arua_registry'),
            ('station_supervisor', 'james.okot@upf.local', 'James', 'Okot', 'UPF-001', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.STATION_SUPERVISOR, 'Officer Commanding Station', 'ASP', 'jinja_station'),
            ('investigating_officer', 'noah.ssemakula@upf.local', 'Noah', 'Ssemakula', 'UPF-002', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.INVESTIGATING_OFFICER, 'Investigating Officer', 'IP', 'jinja_station'),
            ('police_liaison', 'esther.nansubuga@upf.local', 'Esther', 'Nansubuga', 'UPF-003', StaffProfile.Organisation.UGANDA_POLICE, StaffProfile.Role.POLICE_LIAISON, 'Police Liaison Officer', 'IP', 'masaka_station'),
        )
        for key, username, first_name, last_name, officer_number, organisation, role, title, rank, office_key in people:
            email = username if '@' in username else f'{username}@odpp.local'
            account, created = Account.objects.update_or_create(
                username=username,
                defaults={'first_name': first_name, 'last_name': last_name, 'email': email, 'is_active': True},
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
                    'effective_from': SEED_START_DATE,
                    'effective_until': None,
                    'recorded_by': dpp_account,
                    'reason': 'Initial operational posting',
                },
            )
            scope_level = StaffScopeAssignment.ScopeLevel.NATIONAL if key in {'dpp', 'deputy', 'director', 'complaints_head', 'internal_affairs', 'registry_officer'} else StaffScopeAssignment.ScopeLevel.OFFICE
            scope_office = None if scope_level == StaffScopeAssignment.ScopeLevel.NATIONAL else profile.current_office
            StaffScopeAssignment.objects.update_or_create(
                staff_member=profile,
                scope_level=scope_level,
                office=scope_office,
                defaults={
                    'assigned_from': SEED_START_DATE,
                    'assigned_until': None,
                    'assigned_by': dpp_account,
                    'reason': 'Initial access assignment',
                },
            )
