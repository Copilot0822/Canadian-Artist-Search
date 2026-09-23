from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .http import JsonHttpClient
from .models import ArtistMatch, ListenedArtist


MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
CANADA_AREA_ID = "71bbafaa-e825-3e15-8ca9-017dcad1748b"


class MusicBrainzClient:
    def __init__(
        self,
        user_agent: str,
        cache_path: Path,
        delay_seconds: float = 1.1,
        timeout: float = 30.0,
    ) -> None:
        self.http = JsonHttpClient(user_agent=user_agent, timeout=timeout)
        self.cache_path = cache_path
        self.delay_seconds = delay_seconds
        self.last_request_at = 0.0
        self.cache = _load_cache(cache_path)

    def count_uncached_artists(self, artists: list[ListenedArtist]) -> int:
        return len(
            {
                _cache_key(artist.name, artist.mbid)
                for artist in artists
                if _cache_key(artist.name, artist.mbid) not in self.cache
            }
        )

    def prefetch_artists(
        self,
        artists: list[ListenedArtist],
        chunk_size: int = 10,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> None:
        pending: list[ListenedArtist] = []
        seen_keys: set[str] = set()
        for artist in artists:
            cache_key = _cache_key(artist.name, artist.mbid)
            if cache_key in self.cache or cache_key in seen_keys:
                continue
            pending.append(artist)
            seen_keys.add(cache_key)

        if not pending:
            return

        total = len(pending)
        processed = 0
        for chunk in _chunks(pending, max(1, chunk_size)):
            try:
                batch_results = self._search_artists_batch([artist.name for artist in chunk])
                for artist in chunk:
                    raw_artist = _best_artist_result(
                        artist.name,
                        batch_results,
                        allow_fallback=False,
                    )
                    match = _artist_match(artist.name, raw_artist, "musicbrainz-batch-search")
                    self.cache[_cache_key(artist.name, artist.mbid)] = _match_to_cache(match)
                    processed += 1
                    if on_progress is not None:
                        on_progress(processed, total, artist.name)
                _save_cache(self.cache_path, self.cache)
            except Exception:
                for artist in chunk:
                    self.find_artist(artist.name, artist.mbid)
                    processed += 1
                    if on_progress is not None:
                        on_progress(processed, total, artist.name)

    def find_artist(self, artist_name: str, mbid: str | None = None) -> ArtistMatch:
        cache_key = _cache_key(artist_name, mbid)
        cached = self.cache.get(cache_key)
        if isinstance(cached, dict):
            return _match_from_cache(cached)

        raw_artist: dict[str, Any] | None = None
        source = "musicbrainz-search"

        if mbid:
            raw_artist = self._get_artist_by_mbid(mbid)
            source = "musicbrainz-mbid"

        if raw_artist is None:
            raw_artist = self._search_artist(artist_name)
            source = "musicbrainz-search"

        match = _artist_match(artist_name, raw_artist, source)
        self.cache[cache_key] = _match_to_cache(match)
        _save_cache(self.cache_path, self.cache)
        return match

    def _search_artists_batch(self, artist_names: list[str]) -> list[object]:
        self._wait_for_rate_limit()
        query = " OR ".join(f"artist:{_lucene_quote(name)}" for name in artist_names)
        payload = self.http.get_json(
            f"{MUSICBRAINZ_API_URL}/artist",
            {
                "query": query,
                "fmt": "json",
                "limit": 100,
            },
        )
        artists = payload.get("artists", [])
        return artists if isinstance(artists, list) else []

    def _get_artist_by_mbid(self, mbid: str) -> dict[str, Any] | None:
        try:
            self._wait_for_rate_limit()
            payload = self.http.get_json(
                f"{MUSICBRAINZ_API_URL}/artist/{mbid}",
                {"fmt": "json"},
            )
        except Exception:
            return None
        return payload if isinstance(payload, dict) and payload.get("id") else None

    def _search_artist(self, artist_name: str) -> dict[str, Any] | None:
        try:
            self._wait_for_rate_limit()
            payload = self.http.get_json(
                f"{MUSICBRAINZ_API_URL}/artist",
                {
                    "query": f"artist:{_lucene_quote(artist_name)}",
                    "fmt": "json",
                    "limit": 10,
                },
            )
        except Exception:
            return None
        artists = payload.get("artists", [])
        if not isinstance(artists, list):
            return None
        return _best_artist_result(artist_name, artists)

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self.last_request_at = time.monotonic()


def _best_artist_result(
    artist_name: str,
    artists: list[object],
    allow_fallback: bool = True,
) -> dict[str, Any] | None:
    normalized_target = _normalize_name(artist_name)
    fallback: dict[str, Any] | None = None

    for artist in artists:
        if not isinstance(artist, dict):
            continue
        if fallback is None:
            fallback = artist
        names = {
            _normalize_name(str(artist.get("name") or "")),
            _normalize_name(str(artist.get("sort-name") or "")),
        }
        if normalized_target in names:
            return artist

    return fallback if allow_fallback else None


def _chunks(items: list[ListenedArtist], chunk_size: int) -> list[list[ListenedArtist]]:
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def _artist_match(artist_name: str, artist: dict[str, Any] | None, source: str) -> ArtistMatch:
    if artist is None:
        return ArtistMatch(
            is_canadian=False,
            matched_name=None,
            mbid=None,
            country=None,
            area=None,
            score=None,
            source=source,
            reason="no MusicBrainz artist match",
        )

    country = _clean_string(artist.get("country"))
    area = _artist_area_name(artist)
    is_canadian, reason = artist_is_canadian(artist)
    return ArtistMatch(
        is_canadian=is_canadian,
        matched_name=_clean_string(artist.get("name")),
        mbid=_clean_string(artist.get("id")),
        country=country,
        area=area,
        score=_parse_score(artist.get("score")),
        source=source,
        reason=reason if is_canadian else f"not Canadian: {reason}",
    )


def artist_is_canadian(artist: dict[str, Any]) -> tuple[bool, str]:
    if _clean_string(artist.get("country")) == "CA":
        return True, "artist country is CA"

    for area_key in ("area", "begin-area", "end-area"):
        area = artist.get(area_key)
        if _area_is_canada(area):
            return True, f"{area_key} is Canada"

    return False, "country/area is not CA"


def _area_is_canada(area: object) -> bool:
    if not isinstance(area, dict):
        return False
    area_id = _clean_string(area.get("id"))
    if area_id == CANADA_AREA_ID:
        return True
    if _clean_string(area.get("name")) == "Canada":
        return True
    for key in ("iso-3166-1-codes", "iso-3166-2-codes"):
        codes = area.get(key, [])
        if not isinstance(codes, list):
            continue
        for code in codes:
            text = _clean_string(code)
            if text == "CA" or text.startswith("CA-"):
                return True
    return False


def _artist_area_name(artist: dict[str, Any]) -> str | None:
    for key in ("area", "begin-area"):
        area = artist.get(key)
        if isinstance(area, dict):
            name = _clean_string(area.get("name"))
            if name:
                return name
    return None


def _normalize_name(name: str) -> str:
    lowered = name.lower()
    lowered = re.sub(r"^the\s+", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def _lucene_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_score(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _cache_key(artist_name: str, mbid: str | None) -> str:
    if mbid:
        return f"mbid:{mbid}"
    return f"name:{_normalize_name(artist_name)}"


def _load_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_cache(cache_path: Path, cache: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temp_path.replace(cache_path)


def _match_to_cache(match: ArtistMatch) -> dict[str, object]:
    return {
        "is_canadian": match.is_canadian,
        "matched_name": match.matched_name,
        "mbid": match.mbid,
        "country": match.country,
        "area": match.area,
        "score": match.score,
        "source": match.source,
        "reason": match.reason,
    }


def _match_from_cache(data: dict[str, object]) -> ArtistMatch:
    return ArtistMatch(
        is_canadian=bool(data.get("is_canadian")),
        matched_name=_clean_string(data.get("matched_name")),
        mbid=_clean_string(data.get("mbid")),
        country=_clean_string(data.get("country")),
        area=_clean_string(data.get("area")),
        score=_parse_score(data.get("score")),
        source=_clean_string(data.get("source")) or "cache",
        reason=_clean_string(data.get("reason")) or "cached match",
    )
