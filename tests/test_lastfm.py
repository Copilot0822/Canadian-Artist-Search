from canadian_artist_search.lastfm import _parse_artist


def test_parse_artist_reads_lastfm_fields() -> None:
    artist = _parse_artist(
        {
            "name": "Joni Mitchell",
            "playcount": "123",
            "url": "https://www.last.fm/music/Joni+Mitchell",
            "mbid": "a6de8ef9-b1a1-4756-97aa-481bbb8a4069",
            "@attr": {"rank": "42"},
        }
    )

    assert artist is not None
    assert artist.name == "Joni Mitchell"
    assert artist.playcount == 123
    assert artist.overall_rank == 42
    assert artist.lastfm_url == "https://www.last.fm/music/Joni+Mitchell"
    assert artist.mbid == "a6de8ef9-b1a1-4756-97aa-481bbb8a4069"


def test_parse_artist_uses_fallback_rank() -> None:
    artist = _parse_artist({"name": "The Tragically Hip", "playcount": "99"}, fallback_rank=7)

    assert artist is not None
    assert artist.overall_rank == 7
