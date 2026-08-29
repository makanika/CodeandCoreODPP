from base64 import b64encode

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import PublicComplaintForm, PublicTrackingForm
from .services import create_complaint, qr_png, verify_tracking_credentials


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
