from django.urls import path

from accounts.views import StaffLoginView

from .views import MyStaffProfileView

urlpatterns = [
    path('sign-in/', StaffLoginView.as_view(), name='staff-login'),
    path('profile/', MyStaffProfileView.as_view(), name='staff-profile'),
]