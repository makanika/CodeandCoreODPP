from django.urls import path

from .views import ComplaintDetailView, OperationalDashboardView

urlpatterns = [
    path('', OperationalDashboardView.as_view(), name='dashboard'),
    path('complaints/<int:pk>/', ComplaintDetailView.as_view(), name='complaint-detail'),
]