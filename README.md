# Canadian Artist Search

Rank the Canadian artists in a Last.fm user's listening history.

The program reads your Last.fm top artists with the Last.fm API, then checks each artist against MusicBrainz metadata. An artist is counted as Canadian when MusicBrainz reports `country=CA` or a Canadian area code. Output includes both the Canadian-only rank and the artist's overall Last.fm rank.

## Setup

1. Create a Last.fm API key from <https://www.last.fm/api/account/create>.
2. Copy `.env.example` to `.env`.
3. Fill in `LASTFM_API_KEY` in `.env`. `LASTFM_USER` is optional; if it is missing, the program asks for the Last.fm username when it starts.
4. Install the uv environment:

```powershell
uv sync
```

## Run

```powershell
uv run python -m canadian_artist_search
```

Useful options:

```powershell
# Try the first 100 artists only.
uv run python -m canadian_artist_search --limit 100

# Save a CSV for spreadsheet use.
uv run python -m canadian_artist_search --output csv --output-file canadian_artists.csv

# Rank a recent period instead of all-time listening.
uv run python -m canadian_artist_search --period 12month
```

By default the script scans every Last.fm `user.getTopArtists` page for the account. MusicBrainz asks clients to be conservative with request rate, so the first full run can take a while. Results are cached in `.cache/canadian_artist_search/musicbrainz_artists.json`, and later runs reuse that cache.

## Notes

- No Last.fm password is needed.
- Last.fm API authentication for this use only needs an API key and public username.
- MusicBrainz classification is only as accurate as MusicBrainz metadata. If a missing or incorrect artist matters, update MusicBrainz or edit/delete the cache entry and rerun.
