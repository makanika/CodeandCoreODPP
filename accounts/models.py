from django.contrib.auth.models import AbstractUser


class Account(AbstractUser):
    class Meta:
        ordering = ['username']
