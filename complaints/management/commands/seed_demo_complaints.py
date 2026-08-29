from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cases.models import CaseReference
from staff.models import StaffProfile

from complaints.models import Complaint, ComplaintCommunication, ComplaintDetermination, ComplaintInquiry
from complaints.services import assign_complaint, classify_type_b, create_complaint, transition_type_b


class Command(BaseCommand):
    help = 'Create fictional DEMO Type B complaint records linked to the pilot case register.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('DEMO complaints can only be seeded while DJANGO_DEBUG is enabled.')
        if Complaint.objects.filter(source_evidence_reference__startswith='DEMO/INTAKE/').exists():
            self.stdout.write('DEMO complaints already exist; no duplicate records were created.')
            return

        profiles = {profile.officer_number: profile for profile in StaffProfile.objects.all()}
        required = {'DEMO-ODPP-003', 'DEMO-ODPP-004', 'DEMO-ODPP-014', 'DEMO-ODPP-015'}
        if required - profiles.keys() or CaseReference.objects.count() < 5:
            raise CommandError('Run seed_demo_staff and seed_demo_cases before seeding DEMO complaints.')

        cases = list(CaseReference.objects.filter(is_demo=True).order_by('reference'))
        director = profiles['DEMO-ODPP-003']
        complaints_head = profiles['DEMO-ODPP-004']
        rsa = profiles['DEMO-ODPP-014']
        inspector = profiles['DEMO-ODPP-015']
        specs = (
            (cases[0], 'Delay in receipt confirmation', 'The complainant has not received confirmation that the file reached the registry.', Complaint.Status.OPEN_RSA),
            (cases[2], 'File movement concern', 'The complainant seeks an update after a dispatched file remained unacknowledged.', Complaint.Status.ESCALATED_REGIONAL),
            (cases[4], 'Perusal delay', 'The complainant reports no communication during the expected perusal period.', Complaint.Status.ESCALATED_HQ),
            (cases[6], 'Outcome communication', 'The complainant seeks confirmation of the recorded decision and next step.', Complaint.Status.RESOLVED_RSA),
            (cases[8], 'Closure communication', 'The complainant reports that a closure outcome was not communicated.', Complaint.Status.RESOLVED_REGIONAL),
        )
        for index, (case, subject, narrative, target_status) in enumerate(specs, start=1):
            complaint = create_complaint(
                intake_channel=Complaint.IntakeChannel.ASSISTED_DESK if index % 2 else Complaint.IntakeChannel.PUBLIC_PORTAL,
                complainant_name=f'DEMO Complainant {index}',
                complainant_phone=f'0700000{index:03d}',
                preferred_contact_channel='PHONE',
                related_case=case,
                supplied_case_reference=case.reference,
                subject=subject,
                narrative=narrative,
                captured_by=complaints_head.account,
                source_evidence_reference=f'DEMO/INTAKE/2026/{index:04d}',
                is_demo=True,
            )
            complaint.public_status = 'Your complaint is being reviewed. We will contact you through your preferred channel.'
            complaint.acknowledged_at = timezone.now()
            complaint.save(update_fields=['public_status', 'acknowledged_at'])
            classify_type_b(complaint, complaints_head)
            assign_complaint(complaint, assignee=rsa, assigned_by=complaints_head, reason='DEMO first review allocation', due_at=case.last_meaningful_update_at, priority=Complaint.Priority.HIGH)
            transition_type_b(complaint, resulting_status=Complaint.Status.OPEN_RSA, actor=rsa, detail='DEMO inquiry opened with responsible RSA.')
            ComplaintInquiry.objects.create(complaint=complaint, opened_by=rsa, summary='DEMO review of the linked complaint-context case record.', requested_action='Confirm the next accountable action and communication outcome.')
            if target_status == Complaint.Status.ESCALATED_REGIONAL:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='DEMO escalation after the responsible-officer review window.', automatic=True)
            elif target_status == Complaint.Status.ESCALATED_HQ:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='DEMO first escalation after review window.', automatic=True)
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_HQ, actor=director, detail='DEMO second escalation to headquarters.', automatic=True)
            elif target_status == Complaint.Status.RESOLVED_RSA:
                transition_type_b(complaint, resulting_status=Complaint.Status.RESOLVED_RSA, actor=rsa, detail='DEMO responsible-officer resolution recorded.')
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.ADMINISTRATIVE_REMEDY, remedy='DEMO approved communication and follow-up action.', determined_by=rsa)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.PHONE, recipient=complaint.complainant_name, outcome='DEMO outcome communicated.', communicated_at=timezone.now(), recorded_by=rsa)
            elif target_status == Complaint.Status.RESOLVED_REGIONAL:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='DEMO regional escalation after review window.', automatic=True)
                transition_type_b(complaint, resulting_status=Complaint.Status.RESOLVED_REGIONAL, actor=inspector, detail='DEMO regional resolution recorded.')
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.UPHELD, remedy='DEMO regional remedy and closure communication.', determined_by=inspector)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.EMAIL, recipient=complaint.complainant_name, outcome='DEMO regional outcome communicated.', communicated_at=timezone.now(), recorded_by=inspector)
        self.stdout.write(self.style.SUCCESS(f'Created {len(specs)} DEMO Type B complaints.'))