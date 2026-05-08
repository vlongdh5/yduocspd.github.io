from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for HRMS. Extended in Task 2."""
    pass
