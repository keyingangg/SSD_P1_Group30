"""Staff Invite Token Schema (Admin diagram: data_invite)."""
import uuid

from django.db import models

from .user_schema import User


class StaffInviteToken(models.Model):
    """One-time staff invitation token issued by an admin.

    The invited user has no usable password until they accept the invite and
    set one themselves — the inviting admin never handles a credential.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="staff_invite_tokens"
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invites"
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "staff_invite_tokens"
