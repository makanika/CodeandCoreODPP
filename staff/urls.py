from django.urls import path

from .views import MyStaffProfileView

urlpatterns = [
    path('profile/', MyStaffProfileView.as_view(), name='staff-profile'),
]