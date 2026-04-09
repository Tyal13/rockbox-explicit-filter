#!/usr/bin/env python3
"""
Explicit Content Tagger for Rockbox iPod
=========================================
Scans a music library, looks up each track against Deezer and YouTube Music
to determine if it's explicit, then writes the result into the file's
comment tag for Rockbox database filtering.

Zero API keys required. Fully autonomous.

Usage:
    python3 explicit-tagger.py [music_dir] [--dry-run] [--report-only]

Options:
    --dry-run       Show what would be tagged without modifying files
    --report-only   Just generate the CSV report, don't tag anything
    --force         Re-check tracks that already have EXPLICIT= in comment
"""

import os
import sys
import csv
import json
import time
import argparse
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime

# Try to import optional dependencies
try:
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, COMM, TXXX, TIT1
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from ytmusicapi import YTMusic
    HAS_YTMUSIC = True
except ImportError:
    HAS_YTMUSIC = False


def deezer_lookup(artist, title, retries=2):
    """Look up explicit status via Deezer API (zero auth)."""
    query = f'artist:"{artist}" track:"{title}"'
    url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=5"

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RockboxExplicitTagger/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if not data.get("data"):
                return None

            # Check all results for an explicit match
            for track in data["data"]:
                track_title = track.get("title", "").lower()
                track_artist = track.get("artist", {}).get("name", "").lower()
                if (similar(title.lower(), track_title) and
                        similar(artist.lower(), track_artist)):
                    return track.get("explicit_lyrics", False)

            # Fallback to first result
            return data["data"][0].get("explicit_lyrics", False)

        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return None


def ytmusic_lookup(yt, artist, title):
    """Look up explicit status via YouTube Music (zero auth)."""
    try:
        results = yt.search(f"{artist} {title}", filter="songs", limit=5)
        if not results:
            return None

        for r in results:
            r_title = r.get("title", "").lower()
            r_artists = " ".join(a.get("name", "") for a in r.get("artists", [])).lower()
            if similar(title.lower(), r_title) and similar(artist.lower(), r_artists):
                return r.get("isExplicit", False)

        return results[0].get("isExplicit", False)

    except Exception:
        return None


def similar(a, b):
    """Simple similarity check — one string contains the core of the other."""
    a = a.strip().lower()
    b = b.strip().lower()
    if not a or not b:
        return False
    # Direct match or containment
    if a == b or a in b or b in a:
        return True
    # Check if first N significant chars match
    a_clean = "".join(c for c in a if c.isalnum())
    b_clean = "".join(c for c in b if c.isalnum())
    if not a_clean or not b_clean:
        return False
    min_len = min(len(a_clean), len(b_clean))
    if min_len >= 4 and a_clean[:min_len] == b_clean[:min_len]:
        return True
    return False


def read_tags(filepath):
    """Read artist and title from audio file."""
    ext = filepath.suffix.lower()
    try:
        if ext == ".flac":
            audio = FLAC(str(filepath))
            if not audio.tags:
                return None
            # FLAC tags: .get() returns lists, case-insensitive keys
            def get_flac(key):
                val = audio.tags.get(key) or audio.tags.get(key.lower()) or audio.tags.get(key.upper())
                if val:
                    return val[0] if isinstance(val, list) else val
                return ""
            return {
                "artist": get_flac("ARTIST") or get_flac("ALBUMARTIST") or "",
                "title": get_flac("TITLE") or "",
                "album": get_flac("ALBUM") or "",
                "comment": get_flac("COMMENT") or "",
            }
        elif ext == ".mp3":
            audio = MP3(str(filepath))
            if not audio.tags:
                return None
            artist = str(audio.tags.get("TPE1", audio.tags.get("TPE2", "")))
            title = str(audio.tags.get("TIT2", ""))
            album = str(audio.tags.get("TALB", ""))
            # Get comment
            comment = ""
            for key in audio.tags:
                if key.startswith("COMM"):
                    comment = str(audio.tags[key])
                    break
            return {
                "artist": artist,
                "title": title,
                "album": album,
                "comment": comment,
            }
    except Exception as e:
        print(f"  WARNING: Could not read tags from {filepath.name}: {e}")
    return None


def write_explicit_tag(filepath, is_explicit):
    """Write explicit=yes/no into comment tag (prepended) and GROUPING tag for WPS display."""
    ext = filepath.suffix.lower()
    label = "explicit=yes" if is_explicit else "explicit=no"
    grouping = "EXPLICIT" if is_explicit else ""

    try:
        if ext == ".flac":
            audio = FLAC(str(filepath))
            if audio.tags is None:
                audio.add_tags()
            # Preserve existing comment but replace/add EXPLICIT marker
            # FLAC tags can be lowercase or uppercase — check both
            existing = ""
            for key in ("COMMENT", "comment"):
                val = audio.tags.get(key)
                if val:
                    existing = val[0] if isinstance(val, list) else val
                    break
            existing = _strip_explicit_marker(existing)
            new_comment = f"{label}; {existing}".strip("; ") if existing else label
            audio.tags["COMMENT"] = [new_comment]
            # Set GROUPING tag for WPS theme conditional display
            audio.tags["GROUPING"] = [grouping] if grouping else [""]
            audio.save()

        elif ext == ".mp3":
            audio = MP3(str(filepath))
            if audio.tags is None:
                audio.add_tags()
            # Write as TXXX:ROCKBOX_EXPLICIT for clean separation
            audio.tags.add(TXXX(encoding=3, desc="ROCKBOX_EXPLICIT", text=[label]))
            # Also update comment for Rockbox compatibility
            existing_comment = ""
            for key in list(audio.tags.keys()):
                if key.startswith("COMM"):
                    existing_comment = str(audio.tags[key])
                    break
            existing_comment = _strip_explicit_marker(existing_comment)
            new_comment = f"{label}; {existing_comment}".strip("; ") if existing_comment else label
            audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=new_comment))
            # Set GROUPING tag (TIT1) for WPS theme conditional display
            audio.tags.add(TIT1(encoding=3, text=[grouping] if grouping else [""]))
            audio.save()

        return True
    except Exception as e:
        print(f"  ERROR writing tag to {filepath.name}: {e}")
        return False


def _strip_explicit_marker(comment):
    """Remove existing explicit=yes/no or EXPLICIT=yes/no from a comment string."""
    parts = [p.strip() for p in comment.split(";")]
    parts = [p for p in parts if not p.lower().startswith("explicit=")]
    return "; ".join(parts)


def scan_library(music_dir):
    """Find all audio files in the music directory."""
    files = []
    for ext in ("*.flac", "*.mp3"):
        files.extend(Path(music_dir).rglob(ext))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Explicit Content Tagger for Rockbox")
    parser.add_argument("music_dir", nargs="?",
                        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "Music"),
                        help="Path to music directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be tagged without modifying files")
    parser.add_argument("--report-only", action="store_true",
                        help="Generate CSV report only, don't tag files")
    parser.add_argument("--force", action="store_true",
                        help="Re-check tracks already tagged with EXPLICIT=")
    args = parser.parse_args()

    if not HAS_MUTAGEN:
        print("ERROR: mutagen is required. Install with: pip install mutagen")
        sys.exit(1)

    music_dir = Path(args.music_dir).resolve()
    if not music_dir.exists():
        print(f"ERROR: Music directory not found: {music_dir}")
        sys.exit(1)

    print(f"Scanning: {music_dir}")
    files = scan_library(music_dir)
    print(f"Found {len(files)} audio files\n")

    # Initialize YouTube Music (optional)
    yt = None
    if HAS_YTMUSIC:
        try:
            yt = YTMusic()
            print("YouTube Music API: ready (fallback)")
        except Exception:
            print("YouTube Music API: unavailable")
    else:
        print("YouTube Music API: not installed (pip install ytmusicapi)")

    print("Deezer API: ready (primary)\n")
    print("=" * 70)

    results = []
    explicit_count = 0
    clean_count = 0
    unknown_count = 0

    for i, filepath in enumerate(files, 1):
        tags = read_tags(filepath)
        if not tags or not tags["title"]:
            print(f"[{i}/{len(files)}] SKIP (no tags): {filepath.name}")
            results.append({
                "file": str(filepath.relative_to(music_dir)),
                "artist": "", "title": "", "album": "",
                "deezer": "", "ytmusic": "", "final": "unknown",
                "action": "skipped"
            })
            unknown_count += 1
            continue

        # Skip if already tagged (unless --force)
        if not args.force and "explicit=" in tags.get("comment", "").lower():
            existing = "yes" if "explicit=yes" in tags["comment"].lower() else "no"
            print(f"[{i}/{len(files)}] CACHED ({existing}): {tags['artist']} - {tags['title']}")
            results.append({
                "file": str(filepath.relative_to(music_dir)),
                "artist": tags["artist"], "title": tags["title"],
                "album": tags["album"],
                "deezer": "", "ytmusic": "", "final": existing,
                "action": "cached"
            })
            if existing == "yes":
                explicit_count += 1
            else:
                clean_count += 1
            continue

        artist = tags["artist"]
        title = tags["title"]

        # Tier 1: Deezer
        deezer_result = deezer_lookup(artist, title)
        time.sleep(0.2)  # Rate limiting

        # Tier 2: YouTube Music (if Deezer inconclusive or as validation)
        yt_result = None
        if yt and (deezer_result is None or deezer_result is True):
            yt_result = ytmusic_lookup(yt, artist, title)
            time.sleep(0.5)  # Rate limiting

        # Determine final verdict
        if deezer_result is True or yt_result is True:
            final = "yes"
            explicit_count += 1
        elif deezer_result is False and (yt_result is False or yt_result is None):
            final = "no"
            clean_count += 1
        elif yt_result is False:
            final = "no"
            clean_count += 1
        else:
            final = "unknown"
            unknown_count += 1

        status = "EXPLICIT" if final == "yes" else ("CLEAN" if final == "no" else "UNKNOWN")
        print(f"[{i}/{len(files)}] {status}: {artist} - {title}"
              f"  [deezer:{deezer_result}, yt:{yt_result}]")

        # Write tag
        if not args.dry_run and not args.report_only and final != "unknown":
            write_explicit_tag(filepath, final == "yes")

        results.append({
            "file": str(filepath.relative_to(music_dir)),
            "artist": artist, "title": title, "album": tags["album"],
            "deezer": str(deezer_result), "ytmusic": str(yt_result),
            "final": final,
            "action": "tagged" if (not args.dry_run and not args.report_only) else "dry-run"
        })

    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {explicit_count} explicit, {clean_count} clean, {unknown_count} unknown")
    print(f"Total: {len(files)} files")

    if args.dry_run:
        print("\n(DRY RUN — no files were modified)")
    elif args.report_only:
        print("\n(REPORT ONLY — no files were modified)")

    # Write CSV report
    report_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "documentation"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"explicit-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file", "artist", "title", "album", "deezer", "ytmusic", "final", "action"
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
