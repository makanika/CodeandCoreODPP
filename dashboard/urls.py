from django.urls import path

from .views import CaseDetailView, ComplaintDetailView, OperationalDashboardView, StaffDirectoryView, StaffWorkloadView

urlpatterns = [
    path('', OperationalDashboardView.as_view(), name='dashboard'),
    path('complaints/<int:pk>/', ComplaintDetailView.as_view(), name='complaint-detail'),
    path('cases/<int:pk>/', CaseDetailView.as_view(), name='case-detail'),
    path('staff/', StaffDirectoryView.as_view(), name='staff-directory'),
    path('staff/<int:pk>/', StaffWorkloadView.as_view(), name='staff-workload'),
]