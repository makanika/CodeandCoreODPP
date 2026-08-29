from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cases.models import CaseReference
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
            (cases[0], 'Delay in receipt confirmation', 'The complainant has not received confirmation that the file reached the registry.', Complaint.Status.OPEN_RSA),
            (cases[2], 'File movement concern', 'The complainant seeks an update after a dispatched file remained unacknowledged.', Complaint.Status.ESCALATED_REGIONAL),
            (cases[4], 'Perusal delay', 'The complainant reports no communication during the expected perusal period.', Complaint.Status.ESCALATED_HQ),
            (cases[6], 'Outcome communication', 'The complainant seeks confirmation of the recorded decision and next step.', Complaint.Status.RESOLVED_RSA),
            (cases[8], 'Closure communication', 'The complainant reports that a closure outcome was not communicated.', Complaint.Status.RESOLVED_REGIONAL),
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
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.ADMINISTRATIVE_REMEDY, remedy='Approved communication and follow-up action.', determined_by=rsa)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.PHONE, recipient=complaint.complainant_name, outcome='Outcome communicated to the complainant.', communicated_at=timezone.now(), recorded_by=rsa)
            elif target_status == Complaint.Status.RESOLVED_REGIONAL:
                transition_type_b(complaint, resulting_status=Complaint.Status.ESCALATED_REGIONAL, actor=inspector, detail='Regional escalation after review window.', automatic=True)
                transition_type_b(complaint, resulting_status=Complaint.Status.RESOLVED_REGIONAL, actor=inspector, detail='Regional resolution recorded.')
                ComplaintDetermination.objects.create(complaint=complaint, finding=ComplaintDetermination.Finding.UPHELD, remedy='Regional remedy and closure communication.', determined_by=inspector)
                ComplaintCommunication.objects.create(complaint=complaint, channel=ComplaintCommunication.Channel.EMAIL, recipient=complaint.complainant_name, outcome='Regional outcome communicated to the complainant.', communicated_at=timezone.now(), recorded_by=inspector)
        self.stdout.write(self.style.SUCCESS(f'Created {len(specs)} Type B complaints.'))
