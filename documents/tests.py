from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from staff.models import StaffProfile

from .models import Document, DocumentComment


class DocumentCommentTests(TestCase):
	def test_comment_records_staff_identity_snapshot(self):
		account = get_user_model().objects.create_user(
			username='demo.rsa',
			first_name='Amina',
			last_name='Kato',
			password='test-password',
		)
		profile = StaffProfile.objects.create(
			account=account,
			officer_number='DEMO-ODPP-014',
			organisation=StaffProfile.Organisation.ODPP,
			role=StaffProfile.Role.RESIDENT_STATE_ATTORNEY,
			job_title='Resident State Attorney',
		)
		document = Document.objects.create(
			file=SimpleUploadedFile('review-form.pdf', b'complaint review form', content_type='application/pdf'),
			original_filename='review-form.pdf',
			content_type='application/pdf',
			file_size=21,
			content_hash='a' * 64,
			category=Document.Category.FORM,
			uploaded_by=account,
		)

		comment = DocumentComment.objects.create(
			document=document,
			author=account,
			body='Please review the attached form before the next escalation.',
		)

		self.assertEqual(comment.author_name, 'Amina Kato')
		self.assertEqual(comment.author_officer_number, profile.officer_number)
		self.assertEqual(comment.author_role, profile.role)