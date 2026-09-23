from __future__ import annotations

from typing import Any

from .http import JsonHttpClient
from .models import ListenedArtist


LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
VALID_PERIODS = {"overall", "7day", "1month", "3month", "6month", "12month"}


class LastFmError(RuntimeError):
    pass


class LastFmClient:
    def __init__(self, api_key: str, user_agent: str, timeout: float = 30.0) -> None:
        self.api_key = api_key
        self.http = JsonHttpClient(user_agent=user_agent, timeout=timeout)

    def get_top_artists(
        self,
        user: str,
        period: str = "overall",
        page_size: int = 1000,
        max_artists: int | None = None,
    ) -> list[ListenedArtist]:
        if period not in VALID_PERIODS:
            valid = ", ".join(sorted(VALID_PERIODS))
            raise ValueError(f"invalid period {period!r}; expected one of: {valid}")
        if page_size <= 0:
            raise ValueError("page_size must be greater than zero")

        artists: list[ListenedArtist] = []
        page = 1
        total_pages: int | None = None

        while total_pages is None or page <= total_pages:
            payload = self._request(
                method="user.gettopartists",
                user=user,
                period=period,
                limit=page_size,
                page=page,
            )
            top_artists = _expect_mapping(payload.get("topartists"), "topartists")
            total_pages = _read_total_pages(top_artists, fallback=page)
            page_artists = top_artists.get("artist", [])
            if not isinstance(page_artists, list) or not page_artists:
                break

            for raw_artist in page_artists:
                artist = _parse_artist(raw_artist, fallback_rank=len(artists) + 1)
                if artist is not None:
                    artists.append(artist)
                if max_artists is not None and len(artists) >= max_artists:
                    return artists

            page += 1

        return artists

    def _request(self, **params: object) -> dict[str, Any]:
        payload = self.http.get_json(
            LASTFM_API_URL,
            {
                **params,
                "api_key": self.api_key,
                "format": "json",
            },
        )
        if "error" in payload:
            message = payload.get("message", "Last.fm API error")
            raise LastFmError(f"{message} (code {payload.get('error')})")
        return payload


def _parse_artist(raw_artist: object, fallback_rank: int | None = None) -> ListenedArtist | None:
    if not isinstance(raw_artist, dict):
        return None

    name = str(raw_artist.get("name") or "").strip()
    if not name:
        return None

    try:
        playcount = int(raw_artist.get("playcount") or 0)
    except (TypeError, ValueError):
        playcount = 0

    mbid = str(raw_artist.get("mbid") or "").strip() or None
    return ListenedArtist(
        name=name,
        playcount=playcount,
        overall_rank=_read_artist_rank(raw_artist, fallback=fallback_rank),
        lastfm_url=str(raw_artist.get("url") or "").strip() or None,
        mbid=mbid,
    )


def _read_artist_rank(raw_artist: dict[str, Any], fallback: int | None) -> int | None:
    attrs = raw_artist.get("@attr", {})
    if isinstance(attrs, dict):
        try:
            return int(attrs.get("rank") or fallback)
        except (TypeError, ValueError):
            pass
    return fallback


def _read_total_pages(top_artists: dict[str, Any], fallback: int) -> int:
    attrs = top_artists.get("@attr", {})
    if not isinstance(attrs, dict):
        return fallback
    try:
        return int(attrs.get("totalPages") or fallback)
    except (TypeError, ValueError):
        return fallback


def _expect_mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LastFmError(f"Last.fm response did not include {name}")
    return value
