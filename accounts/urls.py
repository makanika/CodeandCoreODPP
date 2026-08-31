from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import LandingView

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('logout/', LogoutView.as_view(), name='staff-logout'),
]