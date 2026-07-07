"""Session Termination Service — admin-initiated session kill (diagram: biz_termination)."""
from .session_manager import invalidate_all_user_sessions


def terminate_user_sessions(target):
    """Kill a user's live session(s) without locking or deleting the account (FSR-C-07)."""
    invalidate_all_user_sessions(target)
