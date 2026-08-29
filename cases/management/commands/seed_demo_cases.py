from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cases.models import CaseAssignment, CaseIdentifier, CaseMovement, CaseReference
from common.models import Office, Region
from staff.models import StaffProfile


def kampala_datetime(year, month, day, hour, minute):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


class Command(BaseCommand):
    help = 'Create or update detailed fictional DEMO complaint-context case records.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('DEMO cases can only be seeded while DJANGO_DEBUG is enabled.')

        offices = {office.code: office for office in Office.objects.all()}
        profiles = {profile.officer_number: profile for profile in StaffProfile.objects.all()}
        required_offices = {'DEMO-JINJA-PS', 'DEMO-MASAKA-CPS', 'DEMO-ARUA-CPS', 'DEMO-NAK-ODPP', 'DEMO-MAS-ODPP', 'DEMO-ARU-ODPP', 'DEMO-NAK-REG', 'DEMO-MAS-REG', 'DEMO-ARU-REG'}
        if required_offices - offices.keys():
            raise CommandError('Run seed_demo_staff before seeding DEMO cases.')

        records = self._records(offices, profiles)
        for record in records:
            case = self._upsert_case(record)
            self._upsert_identifiers(case, record, offices, profiles)
            self._upsert_movements(case, record, offices, profiles)
            self._upsert_assignment(case, record, profiles)
        self.stdout.write(self.style.SUCCESS(f'Created or updated {len(records)} DEMO case records.'))

    def _profile(self, profiles, officer_number):
        try:
            return profiles[officer_number]
        except KeyError as exc:
            raise CommandError(f'Missing DEMO staff profile {officer_number}. Run seed_demo_staff first.') from exc

    def _records(self, offices, profiles):
        station_specs = (
            ('JINJA', 'DEMO-JINJA-PS', 'DEMO-NAK', 'DEMO-NAK-ODPP', 'DEMO-NAK-REG', 'DEMO-UPF-002'),
            ('MAS', 'DEMO-MASAKA-CPS', 'DEMO-MAS', 'DEMO-MAS-ODPP', 'DEMO-MAS-REG', 'DEMO-UPF-003'),
            ('ARU', 'DEMO-ARUA-CPS', 'DEMO-ARU', 'DEMO-ARU-ODPP', 'DEMO-ARU-REG', 'DEMO-ODPP-014'),
        )
        stages = (
            (CaseReference.Stage.POLICE_OPENED, CaseReference.Sensitivity.STANDARD, 'Initial complaint context recorded; station follow-up is pending.', 2),
            (CaseReference.Stage.POLICE_PREPARING, CaseReference.Sensitivity.RESTRICTED, 'Complainant reports delayed feedback while station records are being prepared.', 4),
            (CaseReference.Stage.DISPATCHED_TO_ODPP, CaseReference.Sensitivity.STANDARD, 'Complainant asks for confirmation that the dispatched file reached the responsible registry.', 5),
            (CaseReference.Stage.ODPP_RECEIVED, CaseReference.Sensitivity.RESTRICTED, 'Complaint context concerns delay between registry receipt and allocation.', 7),
            (CaseReference.Stage.UNDER_PERUSAL, CaseReference.Sensitivity.CONFIDENTIAL, 'Complaint context concerns a perusal delay and absent communication of the next step.', 10),
            (CaseReference.Stage.DFI_ISSUED, CaseReference.Sensitivity.RESTRICTED, 'Complaint context concerns unclear follow-up after further investigation was directed.', 13),
            (CaseReference.Stage.SANCTIONED, CaseReference.Sensitivity.STANDARD, 'Complaint context concerns confirmation of the prosecution decision and next communication.', 16),
            (CaseReference.Stage.BEFORE_COURT, CaseReference.Sensitivity.RESTRICTED, 'Complaint context concerns custody and status communication after court transfer.', 19),
            (CaseReference.Stage.CLOSED, CaseReference.Sensitivity.STANDARD, 'Complaint context concerns final communication and retrieval of the closure outcome.', 22),
        )
        records = []
        for index, (stage, sensitivity, context, day) in enumerate(stages, start=1):
            prefix, station_code, region_code, odpp_code, registry_code, handler_number = station_specs[(index - 1) % len(station_specs)]
            handler = self._profile(profiles, handler_number)
            rsa = self._profile(profiles, 'DEMO-ODPP-014')
            current_office = offices[station_code] if stage in {CaseReference.Stage.POLICE_OPENED, CaseReference.Stage.POLICE_PREPARING} else offices[odpp_code]
            if stage == CaseReference.Stage.DISPATCHED_TO_ODPP:
                current_office = offices[station_code]
            records.append({
                'reference': f'DEMO/CASE/{prefix}/2026/{index:04d}',
                'title': f'DEMO complaint-context record {prefix}-{index:04d}',
                'context': context,
                'stage': stage,
                'sensitivity': sensitivity,
                'station_code': station_code,
                'region_code': region_code,
                'current_office_code': current_office.code,
                'handler': handler,
                'rsa': rsa if stage not in {CaseReference.Stage.POLICE_OPENED, CaseReference.Stage.POLICE_PREPARING} else None,
                'opened_on': date(2026, 7, min(day, 28)),
                'expected_action_on': date(2026, 9, min(day, 28)),
                'updated_at': kampala_datetime(2026, 8, min(day, 28), 10, 30),
                'registry_code': registry_code,
                'identifiers': (
                    ('SD_OB', f'{prefix}/SD/2026/{400 + index}', station_code, date(2026, 7, min(day, 28))),
                    ('CRB', f'{prefix}/CRB/2026/{900 + index}', station_code, date(2026, 7, min(day + 1, 28))),
                    ('ODPP', f'{prefix}/ODPP/2026/{120 + index}', odpp_code, date(2026, 8, min(day, 28))),
                ),
            })
        return records

    def _upsert_case(self, record):
        region = Region.objects.get(code=record['region_code'])
        office = Office.objects.get(code=record['current_office_code'])
        station = Office.objects.get(code=record['station_code'])
        return CaseReference.objects.update_or_create(
            reference=record['reference'],
            defaults={
                'title': record['title'],
                'complaint_context': record['context'],
                'stage': record['stage'],
                'sensitivity': record['sensitivity'],
                'originating_station': station,
                'responsible_region': region,
                'current_office': office,
                'current_custodian': record['handler'],
                'allocated_to': record['rsa'],
                'opened_on': record['opened_on'],
                'expected_action_on': record['expected_action_on'],
                'last_meaningful_update_at': record['updated_at'],
                'is_demo': True,
            },
        )[0]

    def _upsert_identifiers(self, case, record, offices, profiles):
        for reference_type, value, office_code, issued_on in record['identifiers']:
            CaseIdentifier.objects.update_or_create(
                reference_type=reference_type,
                value=value,
                defaults={
                    'case': case,
                    'issuing_office': offices[office_code],
                    'issued_on': issued_on,
                    'is_verified': True,
                    'verified_by': record['handler'],
                },
            )

    def _upsert_movements(self, case, record, offices, profiles):
        station = offices[record['station_code']]
        registry = offices[record['registry_code']]
        movement_specs = (
            (CaseMovement.MovementType.DISPATCH, station, registry, record['handler'], None, 'DEMO station file cover and verified SD/CRB references', False),
            (CaseMovement.MovementType.RECEIPT, registry, offices[record['current_office_code']], record['handler'], record['rsa'], 'DEMO registry receipt and complaint-context reference pack', True),
        )
        for sequence, (movement_type, sent_from, sent_to, sent_by, received_by, contents, acknowledged) in enumerate(movement_specs, start=1):
            CaseMovement.objects.update_or_create(
                case=case,
                movement_type=movement_type,
                moved_at=record['updated_at'].replace(hour=8 + sequence),
                defaults={
                    'sent_from': sent_from,
                    'sent_to': sent_to,
                    'sent_by': sent_by,
                    'received_by': received_by,
                    'received_at': record['updated_at'].replace(hour=9 + sequence) if acknowledged else None,
                    'declared_contents': contents,
                    'receipt_acknowledged': acknowledged,
                    'note': 'DEMO movement event for complaint-routing demonstration.',
                },
            )

    def _upsert_assignment(self, case, record, profiles):
        if not record['rsa']:
            return
        CaseAssignment.objects.update_or_create(
            case=case,
            assignee=record['rsa'],
            ended_at__isnull=True,
            defaults={
                'assigned_by': self._profile(profiles, 'DEMO-ODPP-003'),
                'reason': 'DEMO complaint-context review allocation',
                'priority': 3,
            },
        )