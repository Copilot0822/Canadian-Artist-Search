from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .lastfm import LastFmClient, LastFmError, VALID_PERIODS
from .musicbrainz import MusicBrainzClient
from .output import write_results
from .ranking import rank_canadian_artists


APP_USER_AGENT = f"canadian-artist-search/{__version__}"


def main(argv: list[str] | None = None) -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--env-file", default=".env")
    bootstrap_args, _ = bootstrap.parse_known_args(argv)
    _load_env_file(Path(bootstrap_args.env_file))

    parser = _build_parser()
    args = parser.parse_args(argv)

    api_key = args.api_key or os.environ.get("LASTFM_API_KEY")
    user = _resolve_lastfm_user(args.user or os.environ.get("LASTFM_USER"))
    if not api_key:
        parser.error("provide --api-key or set LASTFM_API_KEY")
    if not user:
        parser.error("provide --user, set LASTFM_USER, or run from an interactive terminal")

    lastfm = LastFmClient(
        api_key=api_key,
        user_agent=f"{APP_USER_AGENT} Last.fm client",
        timeout=args.timeout,
    )
    musicbrainz = MusicBrainzClient(
        user_agent=_musicbrainz_user_agent(args.musicbrainz_contact),
        cache_path=args.cache,
        delay_seconds=args.musicbrainz_delay,
        timeout=args.timeout,
    )

    try:
        if not args.quiet:
            print(
                f"Fetching Last.fm top artists for {user} ({args.period})...",
                file=sys.stderr,
            )
        listened_artists = lastfm.get_top_artists(
            user=user,
            period=args.period,
            page_size=args.page_size,
            max_artists=args.limit,
        )
    except LastFmError as error:
        print(f"Last.fm error: {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        uncached = musicbrainz.count_uncached_artists(listened_artists)
        print(
            f"Classifying {len(listened_artists)} artists with MusicBrainz metadata "
            f"({uncached} uncached)...",
            file=sys.stderr,
        )
    musicbrainz.prefetch_artists(
        listened_artists,
        chunk_size=args.musicbrainz_batch_size,
        on_progress=None if args.quiet else _progress,
    )

    ranked = rank_canadian_artists(
        listened_artists,
        musicbrainz.find_artist,
    )
    if not args.quiet:
        print(f"Found {len(ranked)} Canadian artists.", file=sys.stderr)

    write_results(ranked, args.output, args.output_file)
    return 0


def _resolve_lastfm_user(configured_user: str | None) -> str | None:
    if configured_user:
        return configured_user.strip() or None
    if not sys.stdin.isatty():
        return None
    entered = input("Last.fm username: ").strip()
    return entered or None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank Canadian artists in a Last.fm user's listening history."
    )
    parser.add_argument("--env-file", default=".env", help="path to a dotenv-style file to load")
    parser.add_argument("--api-key", help="Last.fm API key; defaults to LASTFM_API_KEY")
    parser.add_argument("--user", help="Last.fm username; defaults to LASTFM_USER")
    parser.add_argument(
        "--period",
        choices=sorted(VALID_PERIODS),
        default="overall",
        help="Last.fm chart period to scan",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="maximum number of Last.fm artists to scan; omit to scan every page",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Last.fm artists to request per page",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".cache/canadian_artist_search/musicbrainz_artists.json"),
        help="MusicBrainz classification cache path",
    )
    parser.add_argument(
        "--musicbrainz-delay",
        type=float,
        default=float(os.environ.get("MUSICBRAINZ_DELAY", "1.1")),
        help="seconds to wait between MusicBrainz requests",
    )
    parser.add_argument(
        "--musicbrainz-batch-size",
        type=int,
        default=10,
        help="artist names to include in each MusicBrainz search request",
    )
    parser.add_argument(
        "--musicbrainz-contact",
        default=os.environ.get("MUSICBRAINZ_CONTACT"),
        help="email or URL added to the MusicBrainz User-Agent",
    )
    parser.add_argument(
        "--output",
        choices=["table", "csv", "json"],
        default="table",
        help="output format",
    )
    parser.add_argument("--output-file", type=Path, help="write output to a file")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    return parser


def _progress(index: int, total: int, artist_name: str) -> None:
    if index == total or index == 1 or index % 25 == 0:
        print(f"[{index}/{total}] {artist_name}", file=sys.stderr)


def _musicbrainz_user_agent(contact: str | None) -> str:
    if contact:
        return f"{APP_USER_AGENT} ({contact})"
    return APP_USER_AGENT


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
