from canadian_artist_search.musicbrainz import artist_is_canadian


def test_artist_is_canadian_from_country() -> None:
    is_canadian, reason = artist_is_canadian({"country": "CA"})

    assert is_canadian
    assert reason == "artist country is CA"


def test_artist_is_canadian_from_area_code() -> None:
    is_canadian, reason = artist_is_canadian(
        {"area": {"name": "Toronto", "iso-3166-2-codes": ["CA-ON"]}}
    )

    assert is_canadian
    assert reason == "area is Canada"


def test_artist_is_not_canadian_when_country_is_elsewhere() -> None:
    is_canadian, reason = artist_is_canadian({"country": "US", "area": {"name": "United States"}})

    assert not is_canadian
    assert reason == "country/area is not CA"
