from django.urls import path

from . import views

urlpatterns = [
    path('complaints/', views.public_hub, name='public-hub'),
    path('complain/', views.lodge_complaint, name='complaint-lodge'),
    path('complain/done/', views.complaint_receipt, name='complaint-receipt'),
    path('track/', views.track_complaint, name='complaint-track'),
    path('desk/complaints/lookup/', views.case_lookup, name='complaint-case-lookup'),
    path('desk/complaints/lookup/<int:case_id>/verify/', views.verify_stakeholder, name='complaint-verify-stakeholder'),
    path('desk/complaints/lookup/<int:case_id>/lodge/', views.guided_lodge, name='complaint-guided-lodge'),
]