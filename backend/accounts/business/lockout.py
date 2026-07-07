from datetime import timedelta
from django.utils import timezone


LOCKOUT_DURATIONS = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=24),
]


def get_next_lockout_duration(lockout_level):
    """
    Escalating lockout duration:
    1st lockout: 1 minute
    2nd lockout: 5 minutes
    3rd lockout: 15 minutes
    4th lockout: 1 hour
    5th and later: 24 hours
    """
    index = min(lockout_level, len(LOCKOUT_DURATIONS) - 1)
    return LOCKOUT_DURATIONS[index]


def apply_escalating_lockout(profile, ip_address):
    """
    Increase lockout level and set the next lockout expiry time.
    """
    duration = get_next_lockout_duration(profile.lockout_level)

    profile.lockout_level += 1
    profile.locked_until = timezone.now() + duration
    profile.last_lockout_ip = ip_address
    profile.last_lockout_at = timezone.now()

    profile.save(update_fields=[
        "lockout_level",
        "locked_until",
        "last_lockout_ip",
        "last_lockout_at",
    ])

    return duration