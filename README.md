# Rockbox Explicit Content Filter

**Automated explicit content detection and filtering for Rockbox-powered music players.**

Automatically identifies explicit tracks in your music library using free music APIs, tags them for Rockbox's database engine, and provides filtered browsing views and a visual "Explicit" badge on the Now Playing screen. No audio data is modified and no API keys are required.

<p align="center">
  <img src="docs/images/now-playing-explicit.jpg" alt="Explicit badge on Now Playing screen" width="300"/>
  <img src="docs/images/now-playing-clean.jpg" alt="Clean track - full width title" width="300"/>
</p>

## Features

- **Zero-config API lookups**: Uses Deezer and YouTube Music APIs. No API keys, no accounts, no setup.
- **Accurate detection**: Cross-references multiple databases for reliable explicit/clean classification
- **Rockbox database filtering**: Browse your library as "Clean Library", "Full Library", or "Explicit Only"
- **Visual Now Playing badge**: Red "Explicit" text appears on the Now Playing screen for explicit tracks
- **Non-destructive**: Only modifies metadata comment tags. Audio data, artist, title, album, genre, and ReplayGain tags are never touched.
- **Incremental processing**: Re-run on growing libraries; already-tagged files are skipped automatically
- **Theme-compatible**: Includes patches for popular themes with a universal WPS patcher for any theme
- **Arr-stack safe**: Compatible with Lidarr, Sonarr, and other music management tools

## Quick Start

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install mutagen ytmusicapi requests
```

### 2. Tag your music library

```bash
# Scan and tag your entire music library
python3 scripts/explicit_tagger.py /path/to/your/Music

# Preview without modifying files
python3 scripts/explicit_tagger.py /path/to/your/Music --dry-run

# Generate report only
python3 scripts/explicit_tagger.py /path/to/your/Music --report-only
```

### 3. Install Rockbox database views

Copy `tagnavi_custom.config` to your player's `.rockbox/` directory:

```bash
cp rockbox/tagnavi_custom.config /Volumes/YOURPLAYER/.rockbox/
```

### 4. Install theme patch (optional)

For the Now Playing "Explicit" badge, apply a theme patch:

```bash
# For Nightpod theme
cp themes/Nightpod.wps /Volumes/YOURPLAYER/.rockbox/wps/Nightpod.wps

# For any other theme, use the universal patcher
python3 scripts/patch_wps.py /Volumes/YOURPLAYER/.rockbox/wps/YourTheme.wps
```

### 5. Rebuild database

On your Rockbox player: **Settings > General Settings > Database > Initialize Now**

## How It Works

### Detection Pipeline

```
Music File                     Deezer API              YouTube Music API
    |                              |                          |
    +-- Read artist/title ---------+-- Look up explicit ------+
                                   |       status             |
                                   v                          v
                            explicit_lyrics: true     isExplicit: True
                                   |                          |
                                   +--------> Consensus <-----+
                                                  |
                                                  v
                                   Write to file comment tag:
                                   "explicit=yes" or "explicit=no"
```

### Tagging Strategy

The tagger writes to two metadata fields:

| Field | Value (Explicit) | Value (Clean) | Purpose |
|-------|------------------|---------------|---------|
| `COMMENT` | `explicit=yes; [existing]` | `explicit=no; [existing]` | Database filtering via `tagnavi_custom.config` |
| `GROUPING` | `EXPLICIT` | *(empty)* | Alternative WPS conditional |

The explicit marker is **prepended** to the comment field so Rockbox's WPS engine can check the first characters using `%ss(0,10,%iC)`.

### Rockbox Integration

**Database Views** (`tagnavi_custom.config`):
- **Clean Library**: Hides all tracks tagged `explicit=yes`
- **Full Library**: Shows everything, no filtering
- **Explicit Only**: Shows only explicit tracks

**WPS Theme Badge**:
The Now Playing screen conditionally displays red "Explicit" text using Rockbox's WPS conditional syntax:

```
%?if(%ss(0,10,%iC),=,explicit=y)<%arExplicit|>
```

This checks the first 10 characters of the comment tag. If they match `explicit=y` (the start of `explicit=yes`), it renders the badge. Clean tracks (`explicit=no`) don't match, so no badge appears.

**Dynamic Title Width**:
Clean tracks get full-width scrolling titles. Explicit tracks have a narrower title viewport to make room for the badge:

```
Clean:    |  Song Title That Scrolls Across Full Width          |
Explicit: |  Song Title Scrolls Here...        Explicit |
```

## Supported Formats

| Format | Tag System | Read | Write |
|--------|-----------|------|-------|
| FLAC | Vorbis Comments | Yes | Yes |
| MP3 | ID3v2 | Yes | Yes |
| M4A/AAC | MP4 Tags | Planned | Planned |
| OGG | Vorbis Comments | Planned | Planned |

## Supported Players

Tested on:
- **iPod Classic 7th Gen** (modded with iFlash adapter), Rockbox 4.0

Should work on any Rockbox-supported player with database and WPS theme support, including:
- iPod Classic 5th/6th/7th Gen
- iPod Video
- iPod Nano 1st/2nd Gen
- Sansa Clip+, Fuze, e200
- iriver H100/H300
- And [many more](https://www.rockbox.org/wiki/TargetStatus)

## Project Structure

```
rockbox-explicit-filter/
├── README.md                      # This file
├── LICENSE                        # MIT License
├── requirements.txt               # Python dependencies
├── scripts/
│   ├── explicit_tagger.py         # Main tagger script
│   └── patch_wps.py               # Universal WPS theme patcher
├── rockbox/
│   └── tagnavi_custom.config      # Database filter views
├── themes/
│   ├── Nightpod.wps.patch         # Patch for Nightpod theme
│   └── README.md                  # Theme patching guide
├── docs/
│   ├── ARCHITECTURE.md            # Technical deep-dive
│   ├── TROUBLESHOOTING.md         # Common issues and fixes
│   ├── API_REFERENCE.md           # Deezer/YouTube Music API details
│   └── images/                    # Screenshots and diagrams
└── examples/
    └── sample_report.csv          # Example tagger output
```

## Configuration

### Tagger Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview results without modifying files |
| `--report-only` | Generate CSV report only |
| `--force` | Re-check previously tagged files |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEZER_RATE_LIMIT` | `0.2` | Seconds between Deezer API calls |
| `YTMUSIC_RATE_LIMIT` | `0.5` | Seconds between YouTube Music API calls |

## Performance

| Library Size | Estimated Time | API Calls |
|-------------|---------------|-----------|
| 500 tracks | ~5 minutes | ~500 |
| 5,000 tracks | ~40 minutes | ~5,000 |
| 10,000 tracks | ~80 minutes | ~10,000 |
| 50,000 tracks | ~7 hours | ~50,000 |

Subsequent runs only process new/untagged files, so incremental updates are fast.

## Safety

### What gets modified
- `COMMENT` metadata tag (prepends `explicit=yes` or `explicit=no`)
- `GROUPING` metadata tag (sets to `EXPLICIT` or empty)

### What is NEVER modified
- Audio data (bitstream is untouched)
- Artist, title, album, genre tags
- ReplayGain values
- Album art
- File structure or naming

### Compatibility with music managers
- **Lidarr**: Safe. Lidarr matches files by path and MusicBrainz IDs, ignores comment/grouping fields.
- **Plex**: Safe. Plex reads its own metadata; comment changes don't affect library matching.
- **MusicBee/foobar2000**: Safe. Comment field visible but not used for library management.
- **iTunes/Apple Music**: Safe. Comment field is a standard metadata field.

## Roadmap

- [x] Deezer API integration (zero-auth explicit detection)
- [x] YouTube Music API fallback
- [x] FLAC and MP3 support
- [x] Rockbox database filtering (tagnavi_custom.config)
- [x] WPS theme "Explicit" badge
- [x] Dynamic title width (full width for clean, narrowed for explicit)
- [x] Incremental processing (skip already-tagged files)
- [ ] M4A/AAC and OGG Vorbis support
- [ ] Universal WPS patcher for any theme
- [ ] Auto-skip explicit tracks mode (for work/family environments)
- [ ] Lyrics-based profanity detection via Genius API
- [ ] Web UI for reviewing and overriding classifications
- [ ] Integration with MusicBrainz Picard plugin

## Contributing

Contributions welcome! See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details on how the system works.

Areas where help is especially appreciated:
- Theme patches for additional Rockbox themes
- Testing on non-iPod Rockbox targets
- M4A/OGG format support
- Improving detection accuracy

## Supporting This Project

If this tool is useful to you, consider supporting its development. Every contribution helps keep the project maintained and funds new features like auto-skip mode and expanded format support.

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?logo=github)](https://github.com/sponsors/Tyal13)

This project is and will always be free and open source.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Credits

- **Adam Herrmann**: Creator and maintainer
- **Rockbox Project**: Open-source firmware that makes this possible
- **Deezer API**: Primary explicit content data source
- **YouTube Music**: Secondary/validation data source
- **Nightpod Theme** by Christian Soffke: Reference theme implementation (CC-BY-SA)

## Acknowledgments

This project was developed as part of a larger effort to bring modern content-awareness features to the Rockbox open-source firmware ecosystem. Special thanks to the Rockbox community for building and maintaining an incredible open-source music player firmware.

---

*Built with care for music lovers who want control over their listening experience.*
