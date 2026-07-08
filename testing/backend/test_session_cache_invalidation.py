import pytest
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore

from accounts.business.session_manager import invalidate_all_user_sessions


class FakeUser:
    id = "11111111-1111-1111-1111-111111111111"


@pytest.mark.django_db
def test_invalidate_evicts_cached_session_not_just_db_row():
    store = DBSessionStore()
    store["_auth_user_id"] = FakeUser.id
    store.save()
    key = store.session_key

    CachedSessionStore = import_module(settings.SESSION_ENGINE).SessionStore

    # Simulate another request/worker reading it back -- populates the
    # per-process cache the way a real authenticated request would.
    reader = CachedSessionStore(session_key=key)
    assert reader.get("_auth_user_id") == FakeUser.id

    invalidate_all_user_sessions(FakeUser())

    # Fresh SessionStore instance for the same key simulates the next
    # incoming request hitting the same worker's cache.
    reader2 = CachedSessionStore(session_key=key)
    assert reader2.get("_auth_user_id") is None
