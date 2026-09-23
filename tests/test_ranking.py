from canadian_artist_search.models import ArtistMatch, ListenedArtist
from canadian_artist_search.ranking import rank_canadian_artists


def test_rank_canadian_artists_filters_and_sorts() -> None:
    listened = [
        ListenedArtist("US Artist", 900, overall_rank=1),
        ListenedArtist("Canadian Artist B", 200, overall_rank=3),
        ListenedArtist("Canadian Artist A", 300, overall_rank=2),
    ]

    def match_artist(name: str, mbid: str | None) -> ArtistMatch:
        return ArtistMatch(
            is_canadian=name.startswith("Canadian"),
            matched_name=name,
            mbid=mbid,
            country="CA" if name.startswith("Canadian") else "US",
            area="Canada" if name.startswith("Canadian") else "United States",
            score=100,
            source="test",
            reason="test",
        )

    ranked = rank_canadian_artists(listened, match_artist)

    assert [artist.name for artist in ranked] == ["Canadian Artist A", "Canadian Artist B"]
    assert [artist.rank for artist in ranked] == [1, 2]
    assert [artist.overall_rank for artist in ranked] == [2, 3]
