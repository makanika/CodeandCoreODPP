from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import StaffLoginView

urlpatterns = [
    path('', StaffLoginView.as_view(), name='staff-login'),
    path('logout/', LogoutView.as_view(), name='staff-logout'),
]