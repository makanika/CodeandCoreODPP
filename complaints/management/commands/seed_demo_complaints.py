from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cases.models import CaseParty, CaseReference
from staff.models import StaffProfile

from complaints.models import Complaint, ComplaintCommunication, ComplaintDetermination, ComplaintInquiry
from complaints.services import assign_complaint, classify_type_b, create_complaint, transition_type_b


class Command(BaseCommand):
    help = 'Create seed Type B complaint records linked to the pilot case register.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Seed complaints can only be created while DJANGO_DEBUG is enabled.')
        if Complaint.objects.filter(is_demo=True).exists():
            self.stdout.write('Seed complaints already exist; no duplicate records were created.')
            return

        profiles = {profile.officer_number: profile for profile in StaffProfile.objects.all()}
        required = {'ODPP-003', 'ODPP-004', 'ODPP-014', 'ODPP-015'}
        if required - profiles.keys() or CaseReference.objects.count() < 5:
            raise CommandError('Run seed_demo_staff and seed_demo_cases before seeding complaints.')

        cases = list(CaseReference.objects.filter(is_demo=True).order_by('reference'))
        director = profiles['ODPP-003']
        complaints_head = profiles['ODPP-004']
        rsa = profiles['ODPP-014']
        inspector = profiles['ODPP-015']
        complainants = (
            ('Grace Namuli', 'CF89021512ABCX', '0700000001', ''),
            ('Robert Ssekandi', 'CM85110734FTLK', '0700000002', ''),
            ('Fatuma Nakirya', 'CF93041256QPMZ', '0700000003', ''),
            ('Ivan Bwambale', 'CM90072298LWDR', '0700000004', ''),
            ('Sarah Achieng', 'CF87061109NBHY', '0700000005', ''),
        )
        specs = (
            (
                cases[0], 'Delay in receipt confirmation',
                'The complainant reports that the case file was dispatched from the station over two weeks ago, but no confirmation has been received that it reached the responsible ODPP registry. Repeated attempts to get an update from the station were unsuccessful, and the complainant is concerned the file may have been mislaid in transit. They are requesting written confirmation of the file\'s current custody and location.',
                Complaint.Status.OPEN_RSA,
            ),
            (
                cases[2], 'File movement concern',
                'The complainant states that the case file was dispatched to the ODPP registry but the receiving office has not acknowledged receipt within the expected window. Follow-up enquiries at the originating station produced no further information on the file\'s status. The complainant is requesting a formal update on the file\'s current custody and an explanation for the delay in acknowledgement.',
                Complaint.Status.ESCALATED_REGIONAL,
            ),
            (
                cases[4], 'Perusal delay',
                'The complainant reports that the file has been with the responsible RSA for perusal well beyond the standard review period, without any communication on progress or an indicative decision date. The complainant has visited the registry twice seeking an update and was told only that the file remained under review. They are asking for a definite timeline and, where the delay is not justified, for the matter to be escalated.',
                Complaint.Status.ESCALATED_HQ,
            ),
            (
                cases[6], 'Outcome communication',
                'The complainant reports that a decision was reportedly made on the file some weeks ago, but they have not received formal confirmation of the outcome or guidance on the next procedural step. The complainant is requesting written confirmation of the recorded decision and clarification of what, if anything, is required of them going forward.',
                Complaint.Status.RESOLVED_RSA,
            ),
            (
                cases[8], 'Closure communication',
                'The complainant states that they were informed informally that the case had been closed, but no formal closure notice or explanation of the outcome was ever issued to them. The complainant is requesting a written closure notice setting out the recorded outcome and the reasons for it.',
                Complaint.Status.RESOLVED_REGIONAL,
            ),
        )
        for index, ((case, subject, narrative, target_status), (complainant_name, complainant_nin, complainant_phone, complainant_email)) in enumerate(zip(specs, complainants), start=1):
            complaint = create_complaint(
                intake_channel=Complaint.IntakeChannel.ASSISTED_DESK if index % 2 else Complaint.IntakeChannel.PUBLIC_PORTAL,
                complainant_name=complainant_name,
                complainant_nin=complainant_nin,
                complainant_phone=complainant_phone,
                complainant_email=complainant_email,
                preferred_contact_channel='PHONE',
                related_case=case,
                supplied_case_reference=case.reference,
                subject=subject,
                narrative=narrative,
                captured_by=complaints_head.account,
                source_evidence_reference=f'INTAKE/2026/{index:04d}',
                is_demo=True,
            )
            CaseParty.objects.update_or_create(
                case=case,
                nin=complainant_nin,
                defaults={
                    'role': CaseParty.Role.COMPLAINANT,
                    'full_name': complainant_name,
                    'phone': complainant_phone,
                    'recorded_by': complaints_head,
                },
            )
            complaint.public_status = 'Your complaint is being reviewed. We will contact you through your preferred channel.'
            complaint.acknowledged_at = timezone.now()
            complaint.save(update_fields=['public_status', 'acknowledged_at'])
            classify_type_b(complaint, complaints_head)
            assign_complaint(complaint, assignee=rsa, assigned_by=complaints_head, reason='First review allocation', due_at=case.last_meaningful_update_at, priority=Complaint.Priority.HIGH)
            transition_type_b(complaint, resulting_status=Complaint.Status.OPEN_RSA, actor=rsa, detail='Inquiry opened with responsible RSA.')
            ComplaintInquiry.objects.create(complaint=complaint, opened_by=rsa, summary='Review of the linked complaint-context case record.', requested_action='Confirm the next accountable action and communication outcome.')
            if target_status == Complaint.Status.ESCALATED_REGIONAL:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='Escalated after the responsible-officer review window.', automatic=True)
            elif target_status == Complaint.Status.ESCALATED_HQ:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='First escalation after review window.', automatic=True)
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_HQ, actor=director, detail='Second escalation to headquarters.', automatic=True)
            elif target_status == Complaint.Status.RESOLVED_RSA:
                transition_type_b(complaint, resulting_status=Complaint.Status.RESOLVED_RSA, actor=rsa, detail='Responsible-officer resolution recorded.')
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.ADMINISTRATIVE_REMEDY, remedy='The responsible RSA has confirmed the recorded decision on the file and directed that written confirmation, together with an explanation of the next procedural step, be issued to the complainant within five working days. The registry has been instructed to update its contact log accordingly.', determined_by=rsa)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.PHONE, recipient=complaint.complainant_name, outcome='Outcome communicated to the complainant.', communicated_at=timezone.now(), recorded_by=rsa)
            elif target_status == Complaint.Status.RESOLVED_REGIONAL:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='Regional escalation after review window.', automatic=True)
                transition_type_b(complaint, resulting_status=Complaint.Status.RESOLVED_REGIONAL, actor=inspector, detail='Regional resolution recorded.')
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.UPHELD, remedy='The regional review upheld the complaint in part: the closure outcome was correctly recorded but the required closure notice was never issued to the complainant. The Regional Inspectorate has directed that a formal closure notice, setting out the recorded outcome and reasons, be issued immediately, and that the registry review its closure-notification checklist to prevent recurrence.', determined_by=inspector)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.EMAIL, recipient=complaint.complainant_name, outcome='Regional outcome communicated to the complainant.', communicated_at=timezone.now(), recorded_by=inspector)
        self.stdout.write(self.style.SUCCESS(f'Created {len(specs)} Type B complaints.'))
