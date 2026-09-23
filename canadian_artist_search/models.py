from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListenedArtist:
    name: str
    playcount: int
    overall_rank: int | None = None
    lastfm_url: str | None = None
    mbid: str | None = None


@dataclass(frozen=True)
class ArtistMatch:
    is_canadian: bool
    matched_name: str | None
    mbid: str | None
    country: str | None
    area: str | None
    score: int | None
    source: str
    reason: str


@dataclass(frozen=True)
class RankedCanadianArtist:
    rank: int
    overall_rank: int | None
    name: str
    playcount: int
    lastfm_url: str | None
    match: ArtistMatch

    def as_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "canadian_rank": self.rank,
            "overall_rank": self.overall_rank,
            "artist": self.name,
            "playcount": self.playcount,
            "lastfm_url": self.lastfm_url,
            "musicbrainz_match": self.match.matched_name,
            "musicbrainz_mbid": self.match.mbid,
            "country": self.match.country,
            "area": self.match.area,
            "match_score": self.match.score,
            "match_source": self.match.source,
            "match_reason": self.match.reason,
        }
