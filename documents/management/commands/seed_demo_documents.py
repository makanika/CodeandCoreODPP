import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from cases.models import CaseDocumentLink, CaseReference
from complaints.models import Complaint, ComplaintDocument
from documents.models import Document, DocumentComment
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
                filename=f'sd-ob-extract-{index:02d}.txt',
                category=Document.Category.COMPLAINT_EVIDENCE,
                description=f'Station diary / occurrence book extract for {case.reference}.',
                body=f'Station diary extract\nCase: {case.reference}\nStation: {case.originating_station}\nRecorded contents: routine complaint-context reference material.',
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
                filename=f'intake-form-{index:02d}.txt',
                category=Document.Category.FORM,
                description=f'Complaint intake form for {complaint.reference}.',
                body=f'Complaint intake form\nReference: {complaint.reference}\nComplainant: {complaint.complainant_name}\nSubject: {complaint.subject}\nChannel: {complaint.get_intake_channel_display()}',
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
                    filename=f'determination-letter-{index:02d}.txt',
                    category=Document.Category.DETERMINATION,
                    description=f'Determination letter for {complaint.reference}.',
                    body=f'Determination letter\nReference: {complaint.reference}\nFinding: recorded in the complaint determination.\nCommunicated to: {complaint.complainant_name}',
                    uploaded_by=rsa,
                )
                ComplaintDocument.objects.get_or_create(
                    complaint=complaint,
                    document=determination_document,
                    defaults={'linked_by': rsa, 'purpose': 'Determination and outcome letter'},
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created or verified {created} documents.'))

    def _make_document(self, *, filename, category, description, body, uploaded_by):
        content = body.encode('utf-8')
        content_hash = hashlib.sha256(content).hexdigest()
        existing = Document.objects.filter(content_hash=content_hash).first()
        if existing:
            return existing
        document = Document(
            original_filename=filename,
            content_type='text/plain',
            file_size=len(content),
            content_hash=content_hash,
            category=category,
            visibility=Document.Visibility.RESTRICTED,
            processing_status=Document.ProcessingStatus.INDEXED,
            description=description,
            uploaded_by=uploaded_by,
            extracted_text=body,
        )
        document.file.save(filename, ContentFile(content), save=False)
        document.save()
        return document
