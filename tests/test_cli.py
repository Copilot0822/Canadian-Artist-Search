from __future__ import annotations

import io

from canadian_artist_search.cli import _resolve_lastfm_user


class _InteractiveStdin(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_resolve_lastfm_user_uses_configured_value() -> None:
    assert _resolve_lastfm_user(" user-name ") == "user-name"


def test_resolve_lastfm_user_returns_none_when_not_interactive() -> None:
    assert _resolve_lastfm_user(None) is None


def test_resolve_lastfm_user_prompts_when_interactive(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", _InteractiveStdin())
    monkeypatch.setattr("builtins.input", lambda prompt: " prompted-user ")

    assert _resolve_lastfm_user(None) == "prompted-user"
