from __future__ import annotations

from collections.abc import Callable

from .models import ArtistMatch, ListenedArtist, RankedCanadianArtist


ArtistMatcher = Callable[[str, str | None], ArtistMatch]
ProgressCallback = Callable[[int, int, str], None]


def rank_canadian_artists(
    listened_artists: list[ListenedArtist],
    match_artist: ArtistMatcher,
    on_progress: ProgressCallback | None = None,
) -> list[RankedCanadianArtist]:
    canadian_artists: list[RankedCanadianArtist] = []
    total = len(listened_artists)

    for index, artist in enumerate(listened_artists, start=1):
        if on_progress is not None:
            on_progress(index, total, artist.name)
        match = match_artist(artist.name, artist.mbid)
        if match.is_canadian:
            canadian_artists.append(
                RankedCanadianArtist(
                    rank=0,
                    overall_rank=artist.overall_rank,
                    name=artist.name,
                    playcount=artist.playcount,
                    lastfm_url=artist.lastfm_url,
                    match=match,
                )
            )

    canadian_artists.sort(key=lambda artist: (-artist.playcount, artist.name.casefold()))
    return [
        RankedCanadianArtist(
            rank=rank,
            overall_rank=artist.overall_rank,
            name=artist.name,
            playcount=artist.playcount,
            lastfm_url=artist.lastfm_url,
            match=artist.match,
        )
        for rank, artist in enumerate(canadian_artists, start=1)
    ]
