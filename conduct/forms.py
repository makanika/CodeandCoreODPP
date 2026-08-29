from django import forms

from staff.models import StaffProfile

from .models import ConductComplaint, ConductDetermination


class TypeAEscalationForm(forms.Form):
    subject_officer = forms.ModelChoiceField(queryset=StaffProfile.objects.filter(is_active=True).select_related('account'), label='Officer the allegation concerns')
    allegation_category = forms.ChoiceField(choices=ConductComplaint.AllegationCategory.choices, label='Allegation category')
    severity = forms.ChoiceField(choices=ConductComplaint.Severity.choices, initial=ConductComplaint.Severity.MEDIUM, label='Severity')
    narrative = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Sealed allegation narrative')

    def clean_subject_officer(self):
        officer = self.cleaned_data['subject_officer']
        return officer


class ConductInvestigatorForm(forms.Form):
    investigator = forms.ModelChoiceField(
        queryset=StaffProfile.objects.filter(is_active=True, role=StaffProfile.Role.INTERNAL_AFFAIRS).select_related('account'),
        label='Assign investigator',
    )


class ConductStatusForm(forms.Form):
    new_status = forms.ChoiceField(choices=ConductComplaint.Status.choices, label='Change status to')
    note = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 2}), label='Note')


class ConductCommentForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Comment')


class ConductDeterminationForm(forms.Form):
    finding = forms.ChoiceField(choices=ConductDetermination.Finding.choices, label='Finding')
    recommended_action = forms.ChoiceField(choices=ConductDetermination.RecommendedAction.choices, label='Recommended action')
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Notes')
