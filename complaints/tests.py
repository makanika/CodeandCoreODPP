from django.contrib.auth.hashers import check_password
from django.test import TestCase

from .models import Complaint


class PublicComplaintFlowTests(TestCase):
	def test_receipt_shows_pin_once_and_tracker_hides_private_content(self):
		response = self.client.post(
			'/complain/',
			{
				'complainant_name': 'DEMO Complainant',
				'complainant_phone': '0700000000',
				'complainant_email': '',
				'supplied_case_reference': '',
				'subject': 'DEMO service delay',
				'narrative': 'temporary public flow private narrative',
			},
		)

		self.assertRedirects(response, '/complain/done/', fetch_redirect_response=False)
		receipt = self.client.session['complaint_receipt']
		complaint = Complaint.objects.get(reference=receipt['reference'])
		self.assertRegex(complaint.reference, r'^CMP/\d{4}/\d{6}$')
		self.assertNotEqual(complaint.tracking_pin_hash, receipt['pin'])
		self.assertTrue(check_password(receipt['pin'], complaint.tracking_pin_hash))

		receipt_response = self.client.get('/complain/done/')
		self.assertContains(receipt_response, 'data:image/png;base64,')
		wrong_pin_response = self.client.post('/track/', {'reference': complaint.reference, 'pin': '000000'})
		self.assertNotContains(wrong_pin_response, 'temporary public flow private narrative')
		self.assertNotContains(wrong_pin_response, 'DEMO/CASE')

# Create your tests here.
