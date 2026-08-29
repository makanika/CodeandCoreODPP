from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView

from documents.models import Document, DocumentComment
from cases.models import CaseReference
from complaints.models import Complaint

from .models import StaffProfile


@method_decorator(ensure_csrf_cookie, name='dispatch')
class MyStaffProfileView(LoginRequiredMixin, DetailView):
    model = StaffProfile
    template_name = 'staff/profile.html'
    context_object_name = 'profile'

    def get_queryset(self):
        return StaffProfile.objects.select_related('account', 'current_office').prefetch_related(
            'postings__office',
            'postings__reports_to__account',
            'scope_assignments__office',
        )

    def get_object(self, queryset=None):
        return self.get_queryset().get(account=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = context['profile']
        primary_posting = next(
            (posting for posting in profile.postings.all() if posting.is_primary),
            None,
        )
        context['primary_posting'] = primary_posting
        context['direct_reportees'] = StaffProfile.objects.filter(
            postings__reports_to=profile,
            postings__is_primary=True,
            is_active=True,
        ).select_related('account', 'current_office').distinct()
        assigned_complaints = Complaint.objects.exclude(
            classification=Complaint.Classification.TYPE_A_HANDOFF,
        ).filter(assigned_to=profile).select_related('related_case', 'assigned_office')
        active_statuses = [
            Complaint.Status.RECEIVED,
            Complaint.Status.OPEN_RSA,
            Complaint.Status.ESCALATED_REGIONAL,
            Complaint.Status.ESCALATED_HQ,
        ]
        active_assigned_complaints = assigned_complaints.filter(status__in=active_statuses)
        context['assigned_complaints'] = active_assigned_complaints.order_by('sla_due_at', '-last_meaningful_update_at')[:5]
        context['assigned_complaint_count'] = active_assigned_complaints.count()
        context['now'] = timezone.now()
        context['overdue_complaint_count'] = active_assigned_complaints.filter(
            sla_due_at__lt=timezone.now(),
        ).count()
        context['allocated_case_count'] = CaseReference.objects.filter(allocated_to=profile).count()
        context['uploaded_document_count'] = Document.objects.filter(uploaded_by=self.request.user).count()
        context['comment_count'] = DocumentComment.objects.filter(author=self.request.user).count()
        return context