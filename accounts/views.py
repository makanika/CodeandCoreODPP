from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from .forms import StaffAuthenticationForm


@method_decorator(ensure_csrf_cookie, name='dispatch')
class StaffLoginView(LoginView):
    authentication_form = StaffAuthenticationForm
    redirect_authenticated_user = True
    template_name = 'accounts/login.html'


class LandingView(TemplateView):
    template_name = 'accounts/landing.html'
