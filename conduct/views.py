from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView

from staff.models import StaffProfile
from staff.permissions import can_access_conduct

from .forms import ConductCommentForm, ConductDeterminationForm, ConductInvestigatorForm, ConductStatusForm
from .models import ConductComplaint
from .services import add_conduct_comment, assign_investigator, change_status, record_determination, visible_conduct_for


class ConductAccessRequiredMixin(UserPassesTestMixin):
    """Refuses the request outright for anyone outside CONDUCT_ROLES. Sealed conduct
    material must be absent, not merely hidden, from views without access."""
    raise_exception = True

    def test_func(self):
        profile = StaffProfile.objects.filter(account=self.request.user).first()
        self.conduct_profile = profile
        return bool(profile and can_access_conduct(profile))


class ConductListView(LoginRequiredMixin, ConductAccessRequiredMixin, ListView):
    model = ConductComplaint
    template_name = 'conduct/list.html'
    context_object_name = 'conduct_complaints'

    def get_queryset(self):
        return visible_conduct_for(self.conduct_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.conduct_profile
        context['is_director'] = self.conduct_profile.role in {StaffProfile.Role.DPP, StaffProfile.Role.DEPUTY_DPP, StaffProfile.Role.HEAD_OF_COMPLAINTS}
        context['can_access_conduct'] = True
        records = context['conduct_complaints']
        context['total_count'] = len(records)
        context['unassigned_count'] = sum(1 for record in records if not record.assigned_investigator_id)
        context['under_inquiry_count'] = sum(1 for record in records if record.status == ConductComplaint.Status.UNDER_INQUIRY)
        context['critical_count'] = sum(1 for record in records if record.severity == ConductComplaint.Severity.CRITICAL)
        return context


class ConductDetailView(LoginRequiredMixin, ConductAccessRequiredMixin, DetailView):
    model = ConductComplaint
    template_name = 'conduct/detail.html'
    context_object_name = 'conduct_complaint'

    def get_queryset(self):
        return visible_conduct_for(self.conduct_profile).prefetch_related('events', 'determinations')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.conduct_profile
        context['profile'] = profile
        context['is_director'] = profile.role in {StaffProfile.Role.DPP, StaffProfile.Role.DEPUTY_DPP, StaffProfile.Role.HEAD_OF_COMPLAINTS}
        context['can_access_conduct'] = True
        context['can_determine'] = profile.role in {StaffProfile.Role.DPP, StaffProfile.Role.DEPUTY_DPP}
        context['investigator_form'] = kwargs.get('investigator_form') or ConductInvestigatorForm()
        context['status_form'] = kwargs.get('status_form') or ConductStatusForm(initial={'new_status': context['conduct_complaint'].status})
        context['comment_form'] = kwargs.get('comment_form') or ConductCommentForm()
        context['determination_form'] = kwargs.get('determination_form') or ConductDeterminationForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile = self.conduct_profile
        action = request.POST.get('action')

        if action == 'assign_investigator':
            form = ConductInvestigatorForm(request.POST)
            if form.is_valid():
                assign_investigator(self.object, investigator=form.cleaned_data['investigator'], actor=profile)
                messages.success(request, f'Assigned to {form.cleaned_data["investigator"]}.')
                return redirect('conduct-detail', pk=self.object.pk)
            return self.render_to_response(self.get_context_data(investigator_form=form))

        if action == 'change_status':
            form = ConductStatusForm(request.POST)
            if form.is_valid():
                try:
                    change_status(self.object, new_status=form.cleaned_data['new_status'], actor=profile, note=form.cleaned_data['note'])
                    messages.success(request, f'Status changed to {self.object.get_status_display()}.')
                    return redirect('conduct-detail', pk=self.object.pk)
                except ValueError as exc:
                    messages.error(request, str(exc))
            return self.render_to_response(self.get_context_data(status_form=form))

        if action == 'comment':
            form = ConductCommentForm(request.POST)
            if form.is_valid():
                add_conduct_comment(self.object, actor=profile, body=form.cleaned_data['body'])
                messages.success(request, 'Comment recorded.')
                return redirect('conduct-detail', pk=self.object.pk)
            return self.render_to_response(self.get_context_data(comment_form=form))

        if action == 'determine':
            if profile.role not in {StaffProfile.Role.DPP, StaffProfile.Role.DEPUTY_DPP}:
                messages.error(request, 'Only the DPP or Deputy DPP can record a determination.')
                return redirect('conduct-detail', pk=self.object.pk)
            form = ConductDeterminationForm(request.POST)
            if form.is_valid():
                record_determination(
                    self.object,
                    finding=form.cleaned_data['finding'],
                    recommended_action=form.cleaned_data['recommended_action'],
                    notes=form.cleaned_data['notes'],
                    determined_by=profile,
                )
                messages.success(request, 'Determination recorded.')
                return redirect('conduct-detail', pk=self.object.pk)
            return self.render_to_response(self.get_context_data(determination_form=form))

        messages.error(request, 'Unrecognised action.')
        return redirect('conduct-detail', pk=self.object.pk)
