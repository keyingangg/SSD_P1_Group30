"""Session Record Schema — diagram: data_session."""
from django.db import models

from .user_schema import User


class UserSessionRecord(models.Model):
    """Tracks known login devices/locations for new-session notifications."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="session_records",
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_session_records"
        unique_together = ("user", "ip_address", "user_agent")

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"
