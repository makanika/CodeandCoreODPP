from django.urls import path

from .views import ConductDetailView, ConductListView

urlpatterns = [
    path('', ConductListView.as_view(), name='conduct-list'),
    path('<int:pk>/', ConductDetailView.as_view(), name='conduct-detail'),
]
