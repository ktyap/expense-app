from django.contrib.auth.models import AbstractUser
from django.db import models


class Member(AbstractUser):
    """A member of the household.

    Members are the only users of the app; there is no separate account model.
    All members have equal permissions and can see and edit every entry.
    """

    name = models.CharField(
        max_length=150,
        help_text='Display name, shown against entries and in the month view.',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or self.get_username()
