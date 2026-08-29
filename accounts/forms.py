from django.contrib.auth.forms import AuthenticationForm


class StaffAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Staff username'
        self.fields['username'].widget.attrs.update({'autocomplete': 'username'})
        self.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})