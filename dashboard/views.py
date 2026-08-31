from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import DetailView

from cases.forms import CaseAssignmentForm, CaseCommentForm, CaseMoveForm, CaseStageForm
from cases.models import CaseReference
from cases.services import add_case_comment, advance_case_stage, assign_case, move_case, visible_cases_for
from complaints.forms import ComplaintAssignmentForm, ComplaintCommentForm
from complaints.models import Complaint, ComplaintEvent
from complaints.services import add_complaint_comment, assign_complaint, handoff_type_a, visible_complaints_for
from conduct.forms import TypeAEscalationForm
from conduct.services import receive_type_a_handoff
from documents.models import Document
from staff.models import StaffProfile
from staff.permissions import can_access_conduct, is_director


class OperationalDashboardView(LoginRequiredMixin, TemplateView):
	template_name = 'dashboard/operational.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		profile = StaffProfile.objects.select_related('account', 'current_office').get(account=self.request.user)
		now = timezone.now()
		complaints = visible_complaints_for(profile).select_related('related_case', 'assigned_to', 'assigned_office')
		cases = visible_cases_for(profile).select_related('originating_station', 'current_office', 'allocated_to')
		direct_reportee_ids = StaffProfile.objects.filter(
			postings__reports_to=profile,
			postings__is_primary=True,
			is_active=True,
		).values_list('pk', flat=True)
		active_statuses = [
			Complaint.Status.RECEIVED,
			Complaint.Status.OPEN_RSA,
			Complaint.Status.ESCALATED_REGIONAL,
			Complaint.Status.ESCALATED_HQ,
		]
		active_complaints = complaints.filter(status__in=active_statuses)
		overdue_complaints = active_complaints.filter(sla_due_at__lt=now)
		due_soon_complaints = active_complaints.filter(sla_due_at__gte=now, sla_due_at__lte=now + timedelta(days=2))
		trend_dates = [timezone.localdate() - timedelta(days=offset) for offset in range(6, -1, -1)]
		context.update(
			profile=profile,
			role_workspace=self._workspace_label(profile.role),
			is_director=is_director(profile),
			can_access_conduct=can_access_conduct(profile),
			now=now,
			complaint_count=active_complaints.count(),
			visible_complaint_count=complaints.count(),
			overdue_count=overdue_complaints.count(),
			due_soon_count=due_soon_complaints.count(),
			unassigned_count=complaints.filter(assigned_to__isnull=True).count(),
			case_count=cases.count(),
			pending_receipt_count=cases.filter(stage='DISPATCHED_TO_ODPP').count(),
			document_count=Document.objects.filter(uploaded_by=self.request.user).count(),
			reportee_workload_count=Complaint.objects.exclude(
				classification=Complaint.Classification.TYPE_A_HANDOFF,
			).filter(assigned_to_id__in=direct_reportee_ids, status__in=active_statuses).count(),
			urgent_complaints=(overdue_complaints | due_soon_complaints).order_by('sla_due_at', '-priority', 'reference')[:8],
			recent_complaints=complaints.order_by('-last_meaningful_update_at')[:7],
			visible_cases=cases.order_by('expected_action_on', '-last_meaningful_update_at')[:6],
			complaint_chart_labels=['Open review', 'Regional', 'HQ', 'Resolved'],
			complaint_chart_values=[
				complaints.filter(status=Complaint.Status.OPEN_RSA).count(),
				complaints.filter(status=Complaint.Status.ESCALATED_REGIONAL).count(),
				complaints.filter(status=Complaint.Status.ESCALATED_HQ).count(),
				complaints.filter(status__in=[Complaint.Status.RESOLVED_RSA, Complaint.Status.RESOLVED_REGIONAL]).count(),
			],
			case_chart_labels=['Police', 'In transit', 'ODPP', 'Perusal', 'Court', 'Closed'],
			case_chart_values=[
				cases.filter(stage__in=['POLICE_OPENED', 'POLICE_PREPARING']).count(),
				cases.filter(stage='DISPATCHED_TO_ODPP').count(),
				cases.filter(stage='ODPP_RECEIVED').count(),
				cases.filter(stage__in=['UNDER_PERUSAL', 'DFI_ISSUED', 'SANCTIONED']).count(),
				cases.filter(stage__in=['BEFORE_COURT', 'HEARING']).count(),
				cases.filter(stage__in=['JUDGEMENT_DELIVERED', 'CLOSED']).count(),
			],
			activity_chart_labels=[trend_date.strftime('%d %b') for trend_date in trend_dates],
			activity_chart_values=[
				ComplaintEvent.objects.filter(complaint__in=complaints, occurred_at__date=trend_date).count()
				for trend_date in trend_dates
			],
		)
		return context

	@staticmethod
	def _workspace_label(role):
		labels = {
			StaffProfile.Role.RESIDENT_STATE_ATTORNEY: 'RSA complaint review workspace',
			StaffProfile.Role.REGIONAL_INSPECTORATE: 'Regional escalation workspace',
			StaffProfile.Role.HEAD_OF_COMPLAINTS: 'Complaints command workspace',
			StaffProfile.Role.DPP: 'National operational overview',
			StaffProfile.Role.DEPUTY_DPP: 'National operational overview',
			StaffProfile.Role.REGISTRY_OFFICER: 'Registry custody and intake workspace',
		}
		return labels.get(role, 'Operational complaints workspace')


class ComplaintListView(LoginRequiredMixin, ListView):
	template_name = 'dashboard/complaint_queue.html'
	context_object_name = 'complaints'
	paginate_by = 25

	def get_queryset(self):
		profile = StaffProfile.objects.get(account=self.request.user)
		queryset = visible_complaints_for(profile).select_related('related_case', 'assigned_to', 'assigned_office')
		status = self.request.GET.get('status')
		if status:
			queryset = queryset.filter(status=status)
		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		profile = StaffProfile.objects.get(account=self.request.user)
		context['profile'] = profile
		context['is_director'] = is_director(profile)
		context['can_access_conduct'] = can_access_conduct(profile)
		context['status_choices'] = Complaint.Status.choices
		context['selected_status'] = self.request.GET.get('status', '')
		context['now'] = timezone.now()
		return context


class ComplaintDetailView(LoginRequiredMixin, DetailView):
	template_name = 'complaints/detail.html'
	context_object_name = 'complaint'

	def get_queryset(self):
		profile = StaffProfile.objects.get(account=self.request.user)
		return visible_complaints_for(profile).select_related(
			'related_case',
			'related_case__originating_station',
			'related_case__current_office',
			'related_case__allocated_to',
			'assigned_to',
			'assigned_office',
		).prefetch_related(
			'events__actor',
			'inquiries__opened_by',
			'determinations__determined_by',
			'communications__recorded_by',
			'document_links__document',
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		profile = StaffProfile.objects.get(account=self.request.user)
		context['profile'] = profile
		context['is_director'] = is_director(profile)
		context['can_access_conduct'] = can_access_conduct(profile)
		context['assignment_form'] = kwargs.get('assignment_form') or ComplaintAssignmentForm(
			requesting_profile=profile,
			initial={'assignee': context['complaint'].assigned_to_id},
		)
		context['comment_form'] = kwargs.get('comment_form') or ComplaintCommentForm()
		context['type_a_form'] = kwargs.get('type_a_form') or TypeAEscalationForm()
		return context

	def post(self, request, *args, **kwargs):
		self.object = self.get_object()
		profile = StaffProfile.objects.get(account=request.user)
		action = request.POST.get('action')
		if action == 'escalate_type_a':
			if not is_director(profile):
				messages.error(request, 'Only directorate-level staff can escalate a complaint to the sealed conduct workflow.')
				return redirect('complaint-detail', pk=self.object.pk)
			if self.object.classification == Complaint.Classification.TYPE_A_HANDOFF:
				messages.error(request, 'This complaint has already been transferred to the conduct workflow.')
				return redirect('complaint-detail', pk=self.object.pk)
			form = TypeAEscalationForm(request.POST)
			if form.is_valid():
				conduct_complaint = receive_type_a_handoff(
					subject_officer=form.cleaned_data['subject_officer'],
					complainant_name=self.object.complainant_name,
					complainant_nin=self.object.complainant_nin,
					complainant_phone=self.object.complainant_phone,
					complainant_email=self.object.complainant_email,
					allegation_category=form.cleaned_data['allegation_category'],
					severity=form.cleaned_data['severity'],
					narrative=form.cleaned_data['narrative'],
					actor=profile,
					source_complaint_reference=self.object.reference,
				)
				handoff_type_a(self.object, actor=profile, conduct_reference=conduct_complaint.reference)
				messages.success(request, f'Complaint {conduct_complaint.reference} escalated to the sealed conduct workflow. This complaint record has been redacted.')
				if can_access_conduct(profile):
					return redirect('conduct-detail', pk=conduct_complaint.pk)
				return redirect('dashboard')
			return self.render_to_response(self.get_context_data(type_a_form=form))
		if action == 'assign':
			if not is_director(profile):
				messages.error(request, 'Only directorate-level staff can reassign a complaint.')
				return redirect('complaint-detail', pk=self.object.pk)
			form = ComplaintAssignmentForm(request.POST, requesting_profile=profile)
			if form.is_valid():
				try:
					assign_complaint(
						self.object,
						assignee=form.cleaned_data['assignee'],
						assigned_by=profile,
						reason=form.cleaned_data['reason'],
					)
					messages.success(request, f'Complaint {self.object.reference} assigned to {form.cleaned_data["assignee"]}.')
					return redirect('complaint-detail', pk=self.object.pk)
				except ValueError as exc:
					messages.error(request, str(exc))
			return self.render_to_response(self.get_context_data(assignment_form=form))
		if action == 'comment':
			form = ComplaintCommentForm(request.POST)
			if form.is_valid():
				add_complaint_comment(self.object, actor=profile, detail=form.cleaned_data['body'])
				messages.success(request, 'Comment recorded.')
				return redirect('complaint-detail', pk=self.object.pk)
			return self.render_to_response(self.get_context_data(comment_form=form))
		messages.error(request, 'Unrecognised action.')
		return redirect('complaint-detail', pk=self.object.pk)


class CaseDetailView(LoginRequiredMixin, DetailView):
	model = CaseReference
	template_name = 'cases/detail.html'
	context_object_name = 'case'

	def get_queryset(self):
		profile = StaffProfile.objects.get(account=self.request.user)
		return visible_cases_for(profile).select_related(
			'originating_station',
			'responsible_region',
			'current_office',
			'current_custodian',
			'allocated_to',
		).prefetch_related(
			'identifiers',
			'movements__sent_from',
			'movements__sent_to',
			'movements__sent_by',
			'movements__received_by',
			'assignments__assignee',
			'comments',
			'document_links__document',
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		profile = StaffProfile.objects.get(account=self.request.user)
		case = context['case']
		context['profile'] = profile
		context['is_director'] = is_director(profile)
		context['can_access_conduct'] = can_access_conduct(profile)
		context['assignment_form'] = kwargs.get('assignment_form') or CaseAssignmentForm(
			requesting_profile=profile,
			initial={'assignee': case.allocated_to_id},
		)
		context['move_form'] = kwargs.get('move_form') or CaseMoveForm(
			requesting_profile=profile,
			initial={'sent_to': case.current_office_id, 'received_by': case.current_custodian_id},
		)
		context['comment_form'] = kwargs.get('comment_form') or CaseCommentForm()
		context['stage_form'] = kwargs.get('stage_form') or CaseStageForm(initial={'new_stage': case.stage})
		return context

	def post(self, request, *args, **kwargs):
		self.object = self.get_object()
		profile = StaffProfile.objects.get(account=request.user)
		action = request.POST.get('action')
		if action == 'advance_stage':
			if not is_director(profile):
				messages.error(request, 'Only directorate-level staff can advance a case stage.')
				return redirect('case-detail', pk=self.object.pk)
			form = CaseStageForm(request.POST)
			if form.is_valid():
				try:
					advance_case_stage(
						self.object,
						new_stage=form.cleaned_data['new_stage'],
						actor=request.user,
						note=form.cleaned_data['note'],
						judgement_outcome=form.cleaned_data['judgement_outcome'],
					)
					messages.success(request, f'Case {self.object.reference} advanced to {self.object.get_stage_display()}.')
					return redirect('case-detail', pk=self.object.pk)
				except ValueError as exc:
					messages.error(request, str(exc))
			return self.render_to_response(self.get_context_data(stage_form=form))
		if action == 'assign':
			if not is_director(profile):
				messages.error(request, 'Only directorate-level staff can allocate a case.')
				return redirect('case-detail', pk=self.object.pk)
			form = CaseAssignmentForm(request.POST, requesting_profile=profile)
			if form.is_valid():
				assign_case(self.object, assignee=form.cleaned_data['assignee'], assigned_by=profile, reason=form.cleaned_data['reason'])
				messages.success(request, f'Case {self.object.reference} allocated to {form.cleaned_data["assignee"]}.')
				return redirect('case-detail', pk=self.object.pk)
			return self.render_to_response(self.get_context_data(assignment_form=form))
		if action == 'move':
			if not is_director(profile):
				messages.error(request, 'Only directorate-level staff can move a case file.')
				return redirect('case-detail', pk=self.object.pk)
			form = CaseMoveForm(request.POST, requesting_profile=profile)
			if form.is_valid():
				move_case(
					self.object,
					movement_type=form.cleaned_data['movement_type'],
					sent_to=form.cleaned_data['sent_to'],
					sent_by=profile,
					received_by=form.cleaned_data['received_by'],
					declared_contents=form.cleaned_data['declared_contents'],
					note=form.cleaned_data['note'],
				)
				messages.success(request, f'Case {self.object.reference} moved to {form.cleaned_data["sent_to"]}.')
				return redirect('case-detail', pk=self.object.pk)
			return self.render_to_response(self.get_context_data(move_form=form))
		if action == 'comment':
			form = CaseCommentForm(request.POST)
			if form.is_valid():
				add_case_comment(self.object, author=request.user, body=form.cleaned_data['body'])
				messages.success(request, 'Comment recorded.')
				return redirect('case-detail', pk=self.object.pk)
			return self.render_to_response(self.get_context_data(comment_form=form))
		messages.error(request, 'Unrecognised action.')
		return redirect('case-detail', pk=self.object.pk)


class DirectorRequiredMixin(UserPassesTestMixin):
	raise_exception = True

	def test_func(self):
		profile = StaffProfile.objects.filter(account=self.request.user).first()
		return bool(profile and is_director(profile))


class StaffDirectoryView(LoginRequiredMixin, DirectorRequiredMixin, ListView):
	model = StaffProfile
	template_name = 'dashboard/staff_directory.html'
	context_object_name = 'staff_members'

	def get_queryset(self):
		active_statuses = [
			Complaint.Status.RECEIVED,
			Complaint.Status.OPEN_RSA,
			Complaint.Status.ESCALATED_REGIONAL,
			Complaint.Status.ESCALATED_HQ,
		]
		return StaffProfile.objects.filter(is_active=True).select_related('account', 'current_office').annotate(
			active_complaint_count=Count(
				'assigned_complaints',
				filter=Q(assigned_complaints__status__in=active_statuses) & ~Q(assigned_complaints__classification=Complaint.Classification.TYPE_A_HANDOFF),
				distinct=True,
			),
			active_case_count=Count('allocated_cases', distinct=True),
		).order_by('-active_complaint_count', 'account__last_name')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['profile'] = StaffProfile.objects.get(account=self.request.user)
		context['is_director'] = True
		context['can_access_conduct'] = can_access_conduct(context['profile'])
		active_statuses = [
			Complaint.Status.RECEIVED,
			Complaint.Status.OPEN_RSA,
			Complaint.Status.ESCALATED_REGIONAL,
			Complaint.Status.ESCALATED_HQ,
		]
		org_complaints = Complaint.objects.exclude(classification=Complaint.Classification.TYPE_A_HANDOFF).filter(status__in=active_statuses)
		context['org_active_complaint_count'] = org_complaints.count()
		context['org_overdue_count'] = org_complaints.filter(sla_due_at__lt=timezone.now()).count()
		context['org_unassigned_count'] = org_complaints.filter(assigned_to__isnull=True).count()
		context['org_active_case_count'] = CaseReference.objects.exclude(stage=CaseReference.Stage.CLOSED).count()
		context['org_staff_count'] = context['staff_members'].count() if hasattr(context['staff_members'], 'count') else len(context['staff_members'])
		return context


class StaffWorkloadView(LoginRequiredMixin, DirectorRequiredMixin, DetailView):
	model = StaffProfile
	template_name = 'dashboard/staff_workload.html'
	context_object_name = 'staff_member'

	def get_queryset(self):
		return StaffProfile.objects.select_related('account', 'current_office').prefetch_related(
			'postings__office',
			'postings__reports_to__account',
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		staff_member = context['staff_member']
		context['profile'] = StaffProfile.objects.get(account=self.request.user)
		context['is_director'] = True
		context['can_access_conduct'] = can_access_conduct(context['profile'])
		active_statuses = [
			Complaint.Status.RECEIVED,
			Complaint.Status.OPEN_RSA,
			Complaint.Status.ESCALATED_REGIONAL,
			Complaint.Status.ESCALATED_HQ,
		]
		context['assigned_complaints'] = Complaint.objects.filter(assigned_to=staff_member).exclude(
			classification=Complaint.Classification.TYPE_A_HANDOFF,
		).filter(status__in=active_statuses).select_related('related_case', 'assigned_office').order_by('sla_due_at')
		context['allocated_cases'] = CaseReference.objects.filter(allocated_to=staff_member).select_related('current_office', 'originating_station').order_by('expected_action_on')
		context['direct_reportees'] = StaffProfile.objects.filter(
			postings__reports_to=staff_member,
			postings__is_primary=True,
			is_active=True,
		).select_related('account', 'current_office').distinct()
		context['primary_posting'] = next((posting for posting in staff_member.postings.all() if posting.is_primary), None)
		context['now'] = timezone.now()
		return context
