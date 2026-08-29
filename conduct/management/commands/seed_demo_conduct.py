from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from staff.models import StaffProfile

from conduct.models import ConductComplaint, ConductDetermination
from conduct.services import assign_investigator, change_status, receive_type_a_handoff, record_determination


class Command(BaseCommand):
    help = 'Create seed sealed conduct records on the isolated conduct database.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Seed conduct records can only be created while DJANGO_DEBUG is enabled.')
        if ConductComplaint.objects.using('conduct').exists():
            self.stdout.write('Seed conduct records already exist; no duplicate records were created.')
            return

        try:
            internal_affairs = StaffProfile.objects.get(officer_number='ODPP-005')
            dpp = StaffProfile.objects.get(officer_number='ODPP-001')
            subject_one = StaffProfile.objects.get(officer_number='ODPP-015')
            subject_two = StaffProfile.objects.get(officer_number='ODPP-016')
        except StaffProfile.DoesNotExist as exc:
            raise CommandError('Run seed_demo_staff before seeding conduct records.') from exc

        record_one = receive_type_a_handoff(
            subject_officer=subject_one,
            complainant_name='Deo Kavuma',
            complainant_nin='CM88051234RTZP',
            complainant_phone='0700000010',
            allegation_category=ConductComplaint.AllegationCategory.DELAY_OR_NEGLECT,
            severity=ConductComplaint.Severity.MEDIUM,
            narrative='The complainant alleges that a case file under this officer\'s custody was left unactioned for over two months despite repeated follow-up requests.',
            actor=internal_affairs,
        )
        record_one.is_demo = True
        record_one.save(using='conduct', update_fields=['is_demo'])
        assign_investigator(record_one, investigator=internal_affairs, actor=dpp)
        change_status(record_one, new_status=ConductComplaint.Status.UNDER_INQUIRY, actor=internal_affairs, note='Initial file review complete; interviews scheduled.')

        record_two = receive_type_a_handoff(
            subject_officer=subject_two,
            complainant_name='Joan Nabatanzi',
            complainant_nin='CF91092233LWQK',
            complainant_email='joan.nabatanzi@example.com',
            allegation_category=ConductComplaint.AllegationCategory.UNPROFESSIONAL_CONDUCT,
            severity=ConductComplaint.Severity.LOW,
            narrative='The complainant alleges discourteous handling of a registry enquiry and a refusal to issue a receipt for submitted documents.',
            actor=internal_affairs,
        )
        record_two.is_demo = True
        record_two.save(using='conduct', update_fields=['is_demo'])
        assign_investigator(record_two, investigator=internal_affairs, actor=dpp)
        change_status(record_two, new_status=ConductComplaint.Status.UNDER_INQUIRY, actor=internal_affairs)
        record_determination(
            record_two,
            finding=ConductDetermination.Finding.NOT_SUBSTANTIATED,
            recommended_action=ConductDetermination.RecommendedAction.NO_ACTION,
            notes='Registry log confirms a receipt was issued; no corroborating evidence of discourtesy found.',
            determined_by=dpp,
        )
        change_status(record_two, new_status=ConductComplaint.Status.CLOSED, actor=dpp, note='Matter closed after determination.')

        self.stdout.write(self.style.SUCCESS('Created 2 seed conduct records.'))
