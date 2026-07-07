"""Promote/demote staff role API (diagram: svc_roles)."""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from core.cross_cutting.audit import log_action, device_fingerprint as _device_fingerprint

from ..business.session_manager import get_client_ip
from ..business.session_termination_service import terminate_user_sessions
from ..business.user_management_service import demote_from_staff, get_admin_target, promote_to_staff
from .permissions import IsSuperUser

logger = logging.getLogger("securebid")


class AdminDemoteStaffView(APIView):
    """Demote an existing staff member back to a regular user (staff only).

    The counterpart to StaffInviteView (promotion). Removes the is_staff
    privilege from an existing account, immediately terminates the target's live
    sessions so the privilege drop takes effect at once, and records the change
    in django-auditlog (admin_role_demoted, NFSR-AC-02). Guards mirror every
    other admin action via get_admin_target: an admin cannot demote their own
    account, a superuser, or an anonymised account.

    Restricted to superusers: revoking staff privileges is a top-tier operation
    reserved for the owner account (least privilege).
    """

    permission_classes = [IsSuperUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = get_admin_target(request, user_id)
        if err:
            return err

        # Only an actual staff member can be demoted — a regular bidder has no
        # elevated role to remove.
        if not target.is_staff:
            return Response(
                {"detail": "This account is not a staff member."},
                status=400,
            )

        demote_from_staff(target)

        # Drop the elevated privilege immediately by killing any live session,
        # forcing the (now regular) user to re-authenticate.
        terminate_user_sessions(target)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_role_demoted",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={
                "target_email": target.email,
                "old_role": "staff",
                "new_role": "user",
            },
        )
        logger.info(
            "Admin %s demoted staff account %s to regular user",
            request.user.email,
            target.email,
        )
        return Response(
            {"detail": "Staff member demoted to regular user.", "role": "Bidder"},
            status=200,
        )


class AdminPromoteUserView(APIView):
    """Promote an existing regular user to staff (staff only).

    The re-promotion counterpart to AdminDemoteStaffView, for restoring staff
    access to an account that already exists (e.g. one that was accidentally
    demoted). Unlike StaffInviteView — which creates a brand-new invited account
    and can only target an unused email — this elevates an existing, already
    registered user. Audit-logged as admin_role_promoted (NFSR-AC-02). Guards
    mirror every other admin action via get_admin_target: an admin cannot
    promote their own account, a superuser, or an anonymised account.

    Restricted to superusers: granting staff privileges is a top-tier operation
    reserved for the owner account (least privilege).
    """

    permission_classes = [IsSuperUser]
    staff_only = True
    http_method_names = ["post"]

    def post(self, request, user_id):
        target, err = get_admin_target(request, user_id)
        if err:
            return err

        if target.is_staff:
            return Response(
                {"detail": "This account is already a staff member."},
                status=400,
            )

        promote_to_staff(target)

        # Force a fresh login so the newly elevated role is reflected in the
        # target's session and admin UI on their next sign-in.
        terminate_user_sessions(target)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        log_action(
            user=request.user,
            action="admin_role_promoted",
            resource_type="User",
            resource_id=target.id,
            ip_address=ip,
            user_agent=ua,
            device_fingerprint=_device_fingerprint(ip, ua),
            role="staff" if request.user.is_staff else "user",
            request_method=request.method,
            endpoint_path=request.path,
            metadata={
                "target_email": target.email,
                "old_role": "user",
                "new_role": "staff",
                "method": "direct",
            },
        )
        logger.info(
            "Admin %s promoted user %s to staff", request.user.email, target.email
        )
        return Response(
            {"detail": "User promoted to staff member.", "role": "Staff"},
            status=200,
        )
