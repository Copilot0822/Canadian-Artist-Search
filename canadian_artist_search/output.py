from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import TextIO

from .models import RankedCanadianArtist


def write_results(
    artists: list[RankedCanadianArtist],
    output_format: str,
    output_file: Path | None,
) -> None:
    handle: TextIO
    close_handle = False
    if output_file is None:
        handle = sys.stdout
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        handle = output_file.open("w", encoding="utf-8", newline="")
        close_handle = True

    try:
        if output_format == "table":
            _write_table(artists, handle)
        elif output_format == "csv":
            _write_csv(artists, handle)
        elif output_format == "json":
            _write_json(artists, handle)
        else:
            raise ValueError(f"unsupported output format: {output_format}")
    finally:
        if close_handle:
            handle.close()


def _write_table(artists: list[RankedCanadianArtist], handle: TextIO) -> None:
    rows = [
        [
            str(artist.rank),
            str(artist.overall_rank or ""),
            str(artist.playcount),
            artist.name,
            artist.match.matched_name or "",
            artist.match.area or artist.match.country or "",
        ]
        for artist in artists
    ]
    headers = ["Canadian rank", "Overall rank", "Plays", "Artist", "MusicBrainz match", "Area"]
    widths = _column_widths(headers, rows)
    handle.write(_format_row(headers, widths) + "\n")
    handle.write(_format_row(["-" * width for width in widths], widths) + "\n")
    for row in rows:
        handle.write(_format_row(row, widths) + "\n")


def _write_csv(artists: list[RankedCanadianArtist], handle: TextIO) -> None:
    fieldnames = list(artists[0].as_dict().keys()) if artists else _empty_fieldnames()
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for artist in artists:
        writer.writerow(artist.as_dict())


def _write_json(artists: list[RankedCanadianArtist], handle: TextIO) -> None:
    json.dump([artist.as_dict() for artist in artists], handle, indent=2)
    handle.write("\n")


def _column_widths(headers: list[str], rows: list[list[str]]) -> list[int]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    return widths


def _format_row(row: list[str], widths: list[int]) -> str:
    padded = [value.rjust(widths[index]) if index < 3 else value.ljust(widths[index]) for index, value in enumerate(row)]
    return "  ".join(padded)


def _empty_fieldnames() -> list[str]:
    return [
        "rank",
        "canadian_rank",
        "overall_rank",
        "artist",
        "playcount",
        "lastfm_url",
        "musicbrainz_match",
        "musicbrainz_mbid",
        "country",
        "area",
        "match_score",
        "match_source",
        "match_reason",
    ]
