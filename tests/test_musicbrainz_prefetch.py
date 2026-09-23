from __future__ import annotations

from canadian_artist_search.models import ListenedArtist
from canadian_artist_search.musicbrainz import MusicBrainzClient


def test_prefetch_artists_batches_and_caches_matches(monkeypatch, tmp_path) -> None:
    client = MusicBrainzClient(
        user_agent="test",
        cache_path=tmp_path / "musicbrainz.json",
        delay_seconds=0,
    )

    calls: list[list[str]] = []

    def fake_batch(names: list[str]) -> list[object]:
        calls.append(names)
        return [
            {"id": "1", "name": "Joni Mitchell", "country": "CA", "score": 100},
            {"id": "2", "name": "Non Canadian", "country": "US", "score": 100},
        ]

    monkeypatch.setattr(client, "_search_artists_batch", fake_batch)

    artists = [
        ListenedArtist("Joni Mitchell", 10),
        ListenedArtist("Non Canadian", 5),
    ]

    client.prefetch_artists(artists, chunk_size=10)

    assert calls == [["Joni Mitchell", "Non Canadian"]]
    assert client.find_artist("Joni Mitchell").is_canadian
    assert not client.find_artist("Non Canadian").is_canadian


def test_prefetch_artists_caches_no_exact_batch_match(monkeypatch, tmp_path) -> None:
    client = MusicBrainzClient(
        user_agent="test",
        cache_path=tmp_path / "musicbrainz.json",
        delay_seconds=0,
    )

    monkeypatch.setattr(
        client,
        "_search_artists_batch",
        lambda names: [{"id": "1", "name": "Different Artist", "country": "CA", "score": 100}],
    )

    client.prefetch_artists([ListenedArtist("Original Artist", 10)], chunk_size=10)
    match = client.find_artist("Original Artist")

    assert not match.is_canadian
    assert match.reason == "no MusicBrainz artist match"
