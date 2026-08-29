from django.urls import path

from . import views

urlpatterns = [
    path('complain/', views.lodge_complaint, name='complaint-lodge'),
    path('complain/done/', views.complaint_receipt, name='complaint-receipt'),
    path('track/', views.track_complaint, name='complaint-track'),
]