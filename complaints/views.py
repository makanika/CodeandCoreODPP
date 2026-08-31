from base64 import b64encode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from cases.models import CaseParty, CaseReference

from .forms import GuidedComplaintForm, PublicComplaintForm, PublicTrackingForm, StakeholderVerifyForm
from .services import create_complaint, find_case_party, qr_png, verify_tracking_credentials


@require_http_methods(['GET'])
def public_hub(request):
    return render(request, 'complaints/public_hub.html')


@require_http_methods(['GET', 'POST'])
def lodge_complaint(request):
    form = PublicComplaintForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        complaint = create_complaint(
            intake_channel='PUBLIC_PORTAL',
            complainant_name=form.cleaned_data['complainant_name'],
            complainant_nin=form.cleaned_data['complainant_nin'],
            complainant_phone=form.cleaned_data['complainant_phone'],
            complainant_email=form.cleaned_data['complainant_email'],
            preferred_contact_channel='EMAIL' if form.cleaned_data['complainant_email'] else 'PHONE',
            related_case=form.cleaned_data.get('related_case'),
            supplied_case_reference=form.cleaned_data['supplied_case_reference'],
            subject=form.cleaned_data['subject'],
            narrative=form.cleaned_data['narrative'],
        )
        request.session['complaint_receipt'] = {'reference': complaint.reference, 'pin': complaint.receipt_pin}
        return redirect('complaint-receipt')
    return render(request, 'complaints/lodge.html', {'form': form})


@require_http_methods(['GET'])
def complaint_receipt(request):
    receipt = request.session.get('complaint_receipt')
    if not receipt:
        raise Http404
    complaint = verify_tracking_credentials(receipt['reference'], receipt['pin'])
    if not complaint:
        raise Http404
    qr_base64 = b64encode(qr_png(complaint)).decode('ascii')
    return render(request, 'complaints/receipt.html', {'reference': complaint.reference, 'pin': receipt['pin'], 'qr_base64': qr_base64})


@require_http_methods(['GET', 'POST'])
def track_complaint(request):
    form = PublicTrackingForm(request.POST or None)
    complaint = None
    if request.method == 'POST' and form.is_valid():
        complaint = verify_tracking_credentials(form.cleaned_data['reference'], form.cleaned_data['pin'])
        if complaint is None:
            messages.error(request, 'The reference or PIN is not recognised. Check both values and try again.')
    return render(request, 'complaints/track.html', {'form': form, 'complaint': complaint})


@login_required
@require_http_methods(['GET'])
def case_lookup(request):
    query = request.GET.get('q', '').strip()
    cases = []
    if query:
        cases = CaseReference.objects.filter(
            Q(reference__icontains=query) | Q(identifiers__value__icontains=query),
        ).distinct().select_related('originating_station')[:20]
    return render(request, 'complaints/case_lookup.html', {'query': query, 'cases': cases})


@login_required
@require_http_methods(['GET', 'POST'])
def verify_stakeholder(request, case_id):
    case = get_object_or_404(CaseReference, pk=case_id)
    form = StakeholderVerifyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        party = find_case_party(case, form.cleaned_data['nin'])
        if party is None:
            messages.error(request, 'No stakeholder record on this case matches that NIN. The complaint cannot be recorded through this route.')
        else:
            request.session['verified_stakeholder'] = {'case_id': case.pk, 'party_id': party.pk}
            return redirect('complaint-guided-lodge', case_id=case.pk)
    return render(request, 'complaints/verify_stakeholder.html', {'case': case, 'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def guided_lodge(request, case_id):
    case = get_object_or_404(CaseReference, pk=case_id)
    verified = request.session.get('verified_stakeholder')
    if not verified or verified.get('case_id') != case.pk:
        messages.error(request, 'Verify the complainant against this case before recording a complaint.')
        return redirect('complaint-verify-stakeholder', case_id=case.pk)
    party = get_object_or_404(CaseParty, pk=verified['party_id'], case=case)
    form = GuidedComplaintForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        complaint = create_complaint(
            intake_channel='ASSISTED_DESK',
            complainant_name=party.full_name,
            complainant_nin=party.nin,
            complainant_phone=party.phone,
            preferred_contact_channel='PHONE' if party.phone else '',
            stakeholder_role=party.role,
            related_case=case,
            subject=form.cleaned_data['subject'],
            narrative=form.cleaned_data['narrative'],
            captured_by=request.user,
        )
        request.session.pop('verified_stakeholder', None)
        request.session['complaint_receipt'] = {'reference': complaint.reference, 'pin': complaint.receipt_pin}
        return redirect('complaint-receipt')
    return render(request, 'complaints/guided_lodge.html', {'case': case, 'party': party, 'form': form})
