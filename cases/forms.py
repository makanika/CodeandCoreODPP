from django import forms

from common.models import Office
from staff.models import StaffProfile
from staff.permissions import assignable_staff

from .models import CaseMovement, CaseReference


class CaseAssignmentForm(forms.Form):
    assignee = forms.ModelChoiceField(queryset=StaffProfile.objects.none(), label='Allocate to')
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label='Reason for allocation')

    def __init__(self, *args, requesting_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_profile is not None:
            self.fields['assignee'].queryset = assignable_staff(requesting_profile).select_related('account')


class CaseMoveForm(forms.Form):
    movement_type = forms.ChoiceField(choices=CaseMovement.MovementType.choices, label='Movement type')
    sent_to = forms.ModelChoiceField(queryset=Office.objects.filter(is_active=True), label='Send to office')
    received_by = forms.ModelChoiceField(queryset=StaffProfile.objects.none(), required=False, label='Receiving custodian')
    declared_contents = forms.CharField(max_length=300, label='Declared contents')
    note = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 2}), label='Note')

    def __init__(self, *args, requesting_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_profile is not None:
            self.fields['received_by'].queryset = assignable_staff(requesting_profile).select_related('account')


class CaseCommentForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Comment')


class CaseStageForm(forms.Form):
    new_stage = forms.ChoiceField(choices=CaseReference.Stage.choices, label='Advance to stage')
    judgement_outcome = forms.ChoiceField(choices=[('', 'Not applicable')] + list(CaseReference.JudgementOutcome.choices), required=False, label='Judgement outcome')
    note = forms.CharField(max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 2}), label='Note')
