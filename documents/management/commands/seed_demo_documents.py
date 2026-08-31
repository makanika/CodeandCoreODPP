import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from cases.models import CaseDocumentLink, CaseIdentifier, CaseReference
from complaints.models import Complaint, ComplaintDocument
from documents.models import Document, DocumentComment
from documents.services import render_letterhead_pdf
from staff.models import StaffProfile


class Command(BaseCommand):
    help = 'Create or update seed documents and link them to seed complaints and cases.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Seed documents can only be created while DJANGO_DEBUG is enabled.')

        try:
            registry_officer = StaffProfile.objects.get(officer_number='ODPP-006').account
            rsa = StaffProfile.objects.get(officer_number='ODPP-014').account
        except StaffProfile.DoesNotExist as exc:
            raise CommandError('Run seed_demo_staff before seeding documents.') from exc

        cases = list(CaseReference.objects.filter(is_demo=True).order_by('reference'))
        complaints = list(Complaint.objects.filter(is_demo=True).order_by('reference'))
        if not cases or not complaints:
            raise CommandError('Run seed_demo_cases and seed_demo_complaints before seeding documents.')

        created = 0
        for index, case in enumerate(cases, start=1):
            document = self._make_document(
                filename=f'sd-ob-extract-{index:02d}.pdf',
                category=Document.Category.COMPLAINT_EVIDENCE,
                description=f'Station diary / occurrence book extract for {case.reference}.',
                content=self._sd_ob_pdf(case),
                content_type='application/pdf',
                extracted_text=case.complaint_context,
                uploaded_by=registry_officer,
            )
            CaseDocumentLink.objects.get_or_create(
                case=case,
                document=document,
                defaults={'linked_by': registry_officer, 'purpose': 'Reference identifier verification'},
            )
            created += 1

        for index, complaint in enumerate(complaints, start=1):
            document = self._make_document(
                filename=f'intake-form-{index:02d}.pdf',
                category=Document.Category.FORM,
                description=f'Complaint intake form for {complaint.reference}.',
                content=self._intake_form_pdf(complaint),
                content_type='application/pdf',
                extracted_text=f'{complaint.subject}\n{complaint.narrative}',
                uploaded_by=rsa,
            )
            ComplaintDocument.objects.get_or_create(
                complaint=complaint,
                document=document,
                defaults={'linked_by': rsa, 'purpose': 'Original intake record'},
            )
            DocumentComment.objects.get_or_create(
                document=document,
                author=rsa,
                body='Intake details verified against the linked case reference.',
            )
            created += 1

            if complaint.status in {Complaint.Status.RESOLVED_RSA, Complaint.Status.RESOLVED_REGIONAL}:
                determination_document = self._make_document(
                    filename=f'determination-letter-{index:02d}.pdf',
                    category=Document.Category.DETERMINATION,
                    description=f'Determination letter for {complaint.reference}.',
                    content=self._determination_pdf(complaint),
                    content_type='application/pdf',
                    extracted_text=complaint.determinations.first().remedy if complaint.determinations.exists() else '',
                    uploaded_by=rsa,
                )
                ComplaintDocument.objects.get_or_create(
                    complaint=complaint,
                    document=determination_document,
                    defaults={'linked_by': rsa, 'purpose': 'Determination and outcome letter'},
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created or verified {created} documents.'))

    def _sd_ob_pdf(self, case):
        sd_identifier = case.identifiers.filter(reference_type=CaseIdentifier.ReferenceType.SD_OB).first()
        custodian = case.current_custodian
        custodian_line = f'{custodian} ({custodian.officer_number}), {custodian.job_title}' if custodian else 'the duty officer on shift'
        entry_paragraph = (
            f"On {case.opened_on:%d %B %Y}, a report was received at {case.originating_station} and entered in the station diary "
            f"under reference {sd_identifier.value if sd_identifier else case.reference}. The entry was recorded by {custodian_line} "
            f"in accordance with the station's standing intake procedure. {case.complaint_context}"
        )
        movement_paragraphs = []
        for movement in case.movements.order_by('moved_at'):
            receipt_note = f'received by {movement.received_by} on {movement.received_at:%d %b %Y, %H:%M}' if movement.received_at else 'not yet acknowledged as received'
            movement_paragraphs.append(
                f"{movement.get_movement_type_display()}: sent from {movement.sent_from} to {movement.sent_to} by {movement.sent_by} "
                f"on {movement.moved_at:%d %b %Y, %H:%M}, declared as “{movement.declared_contents}” — {receipt_note}.",
            )
        if not movement_paragraphs:
            movement_paragraphs = ['No movement has been recorded against this file since the station diary entry was made.']
        position_paragraph = f'The case is currently at the {case.get_stage_display()} stage, held at {case.current_office}'
        if case.current_custodian:
            position_paragraph += f' under {case.current_custodian}'
        if case.allocated_to:
            position_paragraph += f' and allocated to {case.allocated_to}'
        position_paragraph += f'. The next expected action falls due on {case.expected_action_on:%d %B %Y}.' if case.expected_action_on else '.'

        return render_letterhead_pdf(
            category_label='Station diary extract',
            title='Station Diary / Occurrence Book Extract',
            reference=sd_identifier.value if sd_identifier else case.reference,
            meta=[
                ('Case reference', case.reference),
                ('Station', case.originating_station),
                ('Stage', case.get_stage_display()),
            ],
            sections=[
                ('Entry particulars', [entry_paragraph]),
                ('Chain of custody', movement_paragraphs),
                ('Current position', [position_paragraph]),
            ],
            generated_by='Registry Officer',
        )

    def _intake_form_pdf(self, complaint):
        case_reference = complaint.related_case.reference if complaint.related_case else (complaint.supplied_case_reference or 'not yet linked')
        contact_detail = complaint.complainant_phone or complaint.complainant_email or 'the details supplied at intake'
        complainant_paragraph = (
            f"{complaint.complainant_name} lodged this complaint through the {complaint.get_intake_channel_display()} channel, "
            f"referencing case {case_reference}. Contact was recorded as {contact_detail}, with a preference for "
            f"{complaint.preferred_contact_channel or 'phone'} follow-up."
        )
        history_paragraphs = [
            f"{event.occurred_at:%d %b %Y, %H:%M} — {event.get_event_type_display()}: {event.detail}"
            + (f' (recorded by {event.actor_name})' if event.actor_name else ' (system-recorded)')
            for event in complaint.events.order_by('occurred_at')
        ]
        if not history_paragraphs:
            history_paragraphs = ['No processing event has been recorded against this complaint yet.']

        return render_letterhead_pdf(
            category_label='Complaint intake form',
            title='Complaint Intake Form',
            reference=complaint.reference,
            meta=[
                ('Complainant', complaint.complainant_name),
                ('Channel', complaint.get_intake_channel_display()),
                ('Case reference', case_reference),
            ],
            sections=[
                ('Complainant particulars', [complainant_paragraph]),
                ('Narrative of complaint', [complaint.narrative]),
                ('Case history to date', history_paragraphs),
            ],
            generated_by='Resident State Attorney',
        )

    def _determination_pdf(self, complaint):
        case_reference = complaint.related_case.reference if complaint.related_case else (complaint.supplied_case_reference or 'not yet linked')
        determination = complaint.determinations.first()
        communication = complaint.communications.order_by('-communicated_at').first()
        background_paragraph = f'This complaint was lodged by {complaint.complainant_name}, concerning: {complaint.subject}. {complaint.narrative}'
        finding_paragraph = (
            f'Finding: {determination.get_finding_display()}. {determination.remedy}'
            if determination else 'The finding and remedy for this complaint have been recorded in the complaint determination.'
        )
        communication_paragraph = (
            f"The outcome was communicated to {communication.recipient} by {communication.get_channel_display()} on "
            f"{communication.communicated_at:%d %B %Y}, recorded by {communication.recorded_by}: {communication.outcome}"
            if communication else 'Communication of this outcome has not yet been recorded.'
        )
        closing_paragraph = (
            'This determination is recorded under the Type B process-complaint procedure. A complainant who remains '
            'dissatisfied with this outcome may request escalation to the next review level within the applicable service window.'
        )

        return render_letterhead_pdf(
            category_label='Determination letter',
            title='Determination & Outcome Letter',
            reference=complaint.reference,
            meta=[
                ('Complainant', complaint.complainant_name),
                ('Status', complaint.get_status_display()),
                ('Case reference', case_reference),
            ],
            sections=[
                ('Background', [background_paragraph]),
                ('Finding and remedy', [finding_paragraph]),
                ('Communication of outcome', [communication_paragraph]),
                ('Further recourse', [closing_paragraph]),
            ],
            generated_by='Resident State Attorney',
        )

    def _make_document(self, *, filename, category, description, content, content_type, extracted_text, uploaded_by):
        content_hash = hashlib.sha256(content).hexdigest()
        existing = Document.objects.filter(content_hash=content_hash).first()
        if existing:
            return existing
        document = Document(
            original_filename=filename,
            content_type=content_type,
            file_size=len(content),
            content_hash=content_hash,
            category=category,
            visibility=Document.Visibility.RESTRICTED,
            processing_status=Document.ProcessingStatus.INDEXED,
            description=description,
            uploaded_by=uploaded_by,
            extracted_text=extracted_text,
        )
        document.file.save(filename, ContentFile(content), save=False)
        document.save()
        return document
