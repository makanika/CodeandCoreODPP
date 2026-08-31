from django import forms

from cases.models import CaseReference
from staff.models import StaffProfile
from staff.permissions import assignable_staff


class PublicComplaintForm(forms.Form):
    complainant_name = forms.CharField(max_length=160, label='Your name')
    complainant_nin = forms.CharField(max_length=14, required=False, label='National ID number (NIN)')
    complainant_phone = forms.CharField(max_length=32, required=False, label='Phone number')
    complainant_email = forms.EmailField(required=False, label='Email address')
    supplied_case_reference = forms.CharField(max_length=100, required=False, label='Case, CRB, or ODPP reference')
    subject = forms.CharField(max_length=240, label='What is your complaint about?')
    narrative = forms.CharField(widget=forms.Textarea, label='Tell us what happened')

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('complainant_phone') and not cleaned_data.get('complainant_email'):
            raise forms.ValidationError('Provide a phone number or email address so we can contact you.')
        supplied_reference = cleaned_data.get('supplied_case_reference')
        if supplied_reference:
            cleaned_data['related_case'] = CaseReference.objects.filter(
                identifiers__value__iexact=supplied_reference,
            ).first() or CaseReference.objects.filter(reference__iexact=supplied_reference).first()
        return cleaned_data


class PublicTrackingForm(forms.Form):
    reference = forms.CharField(max_length=32, label='Complaint reference')
    pin = forms.CharField(min_length=6, max_length=6, label='Six-digit PIN', widget=forms.PasswordInput)


class StakeholderVerifyForm(forms.Form):
    nin = forms.CharField(max_length=14, label='National ID number (NIN)')


class GuidedComplaintForm(forms.Form):
    subject = forms.CharField(max_length=240, label='What is the complaint about?')
    narrative = forms.CharField(widget=forms.Textarea, label='Record what the complainant reported')


class ComplaintAssignmentForm(forms.Form):
    assignee = forms.ModelChoiceField(queryset=StaffProfile.objects.none(), label='Assign to')
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label='Reason for assignment')

    def __init__(self, *args, requesting_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_profile is not None:
            self.fields['assignee'].queryset = assignable_staff(requesting_profile).select_related('account')


class ComplaintCommentForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Comment')