from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView

from cases.services import visible_cases_for
from complaints.models import Complaint, ComplaintEvent
from complaints.services import visible_complaints_for
from documents.models import Document
from staff.models import StaffProfile


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
			case_chart_labels=['Police', 'In transit', 'ODPP', 'Perusal', 'Outcome'],
			case_chart_values=[
				cases.filter(stage__in=['POLICE_OPENED', 'POLICE_PREPARING']).count(),
				cases.filter(stage='DISPATCHED_TO_ODPP').count(),
				cases.filter(stage='ODPP_RECEIVED').count(),
				cases.filter(stage__in=['UNDER_PERUSAL', 'DFI_ISSUED']).count(),
				cases.filter(stage__in=['SANCTIONED', 'BEFORE_COURT', 'CLOSED']).count(),
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
