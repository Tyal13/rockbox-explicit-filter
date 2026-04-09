# Architecture

## System Overview

The Rockbox Explicit Content Filter is a three-layer system that bridges external music metadata services with Rockbox's on-device database engine and theme rendering system.

```
┌─────────────────────────────────────────────────────────┐
│                    USER'S COMPUTER                       │
│                                                          │
│  ┌──────────────┐    ┌─────────────┐    ┌────────────┐  │
│  │ Music Library │───>│   Tagger    │───>│  Tagged     │  │
│  │ (FLAC/MP3)   │    │   Script    │    │  Files      │  │
│  └──────────────┘    └──────┬──────┘    └─────┬──────┘  │
│                             │                  │         │
│                     ┌───────┴───────┐         │         │
│                     │   Free APIs   │         │         │
│                     │ ┌───────────┐ │         │         │
│                     │ │  Deezer   │ │         │         │
│                     │ └───────────┘ │         │         │
│                     │ ┌───────────┐ │         │         │
│                     │ │ YT Music  │ │         │         │
│                     │ └───────────┘ │         │         │
│                     └───────────────┘         │         │
│                                               │         │
└───────────────────────────────────────────────┼─────────┘
                                                │
                                          Sync to device
                                                │
┌───────────────────────────────────────────────┼─────────┐
│                  ROCKBOX PLAYER                │         │
│                                               v         │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────┐   │
│  │  tagnavi_     │    │  Database   │    │  Music   │   │
│  │  custom.config│───>│  Engine     │<───│  Files   │   │
│  └──────────────┘    └──────┬──────┘    └──────────┘   │
│                             │                           │
│                     ┌───────┴───────┐                   │
│                     │  WPS Theme    │                   │
│                     │  Engine       │                   │
│                     └───────┬───────┘                   │
│                             │                           │
│                     ┌───────┴───────┐                   │
│                     │  Now Playing  │                   │
│                     │  Screen       │                   │
│                     │               │                   │
│                     │  Song Title  Explicit             │
│                     │  Artist Name             │        │
│                     └───────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Component Deep-Dive

### 1. Explicit Tagger (`scripts/explicit_tagger.py`)

The tagger is a standalone Python script that operates in four phases:

#### Phase 1: Library Scan
```python
# Walks the music directory recursively
# Identifies FLAC and MP3 files
# Reads existing tags to extract artist + title
files = scan_library(music_dir)  # Returns sorted list of Path objects
```

#### Phase 2: Tag Reading
FLAC and MP3 files store metadata differently:

| Format | Tag System | Artist Key | Title Key | Comment Key |
|--------|-----------|------------|-----------|-------------|
| FLAC | Vorbis Comments | `ARTIST` or `artist` | `TITLE` or `title` | `COMMENT` or `comment` |
| MP3 | ID3v2 Frames | `TPE1` (lead artist) | `TIT2` (title) | `COMM` (comment) |

**Key implementation detail**: FLAC Vorbis Comments have case-insensitive keys, but the Python `mutagen` library's `.get()` method returns lists while iteration yields strings. The tagger normalizes this by using `.get()` with fallback key casing.

#### Phase 3: API Lookup

**Tier 1 — Deezer (Primary)**:
```
GET https://api.deezer.com/search?q=artist:"X" track:"Y"&limit=5
Response: { data: [{ explicit_lyrics: true/false, ... }] }
```
- Zero authentication required
- Returns `explicit_lyrics` boolean
- Rate limit: ~0.2s between requests (self-imposed)
- Fuzzy matching: compares returned artist/title against query to find best match

**Tier 2 — YouTube Music (Fallback)**:
```python
yt = YTMusic()  # No auth needed
results = yt.search(f"{artist} {title}", filter="songs", limit=5)
# Returns: [{ isExplicit: True/False, ... }]
```
- Only queried when Deezer returns explicit=True (for validation) or None (not found)
- Rate limit: ~0.5s between requests
- Uses `ytmusicapi` Python library

**Consensus Logic**:
```
if deezer=True OR ytmusic=True  → explicit=yes
if deezer=False AND ytmusic=any → explicit=no
if deezer=None AND ytmusic=False → explicit=no
if deezer=None AND ytmusic=None → unknown (not tagged)
```

#### Phase 4: Tag Writing

The tagger writes two fields:

**COMMENT field** (prepended):
```
Before: "Exact Audio Copy V1.6"
After:  "explicit=yes; Exact Audio Copy V1.6"
```

The explicit marker is prepended (not appended) so Rockbox's WPS `%ss()` function can check the first N characters without needing to know the comment's total length.

**GROUPING field** (set):
```
Explicit tracks: GROUPING = "EXPLICIT"
Clean tracks:    GROUPING = ""
```

This provides an alternative WPS conditional path via `%ik` for themes that support it.

### 2. Database Filter (`tagnavi_custom.config`)

Rockbox's database engine supports custom browsing views through `tagnavi_custom.config`. This file defines menu entries that appear in the Database browser.

#### Syntax

```
#! rockbox/tagbrowser/2.0          # Required header

%menu_start "id" "Display Name"     # Define a menu section

"Menu Entry" -> navigation ? filter -> more_navigation
```

#### Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `~` | Contains | `comment ~ "explicit=yes"` |
| `!~` | Does not contain | `comment !~ "explicit=yes"` |
| `=` | Equals | `genre = "Rock"` |
| `!=` | Not equals | `genre != "Classical"` |
| `^` | Starts with | `filename ^ "/Music/"` |

#### Our Implementation

```
# Clean Library — excludes explicit tracks
"Artists" -> artist ? comment !~ "explicit=yes" -> album -> title

# Explicit Only — shows only explicit tracks  
"Artists" -> artist ? comment ~ "explicit=yes" -> album -> title
```

The `!~` operator checks if the comment field does NOT contain `explicit=yes`. This works regardless of where in the comment the marker appears, providing resilience against different tag orderings.

### 3. WPS Theme Integration

Rockbox's WPS (While Playing Screen) theme engine supports conditional rendering based on metadata tags.

#### Available Metadata Tags in WPS

| Tag | Description | Example |
|-----|-------------|---------|
| `%it` | Track title | "Popular Monster" |
| `%ia` | Artist | "Falling in Reverse" |
| `%id` | Album | "Popular Monster" |
| `%ig` | Genre | "Rock" |
| `%ic` | Composer | "Ronnie Radke" |
| `%iC` | Comment | "explicit=yes; [original comment]" |
| `%ik` | Grouping | "EXPLICIT" |
| `%fc` | File codec (numeric) | 7 (FLAC) |

#### The Explicit Badge

The badge uses `%iC` (comment tag) with `%ss()` (substring) for conditional display:

```
# Extract first 10 characters of comment
# Compare against "explicit=y" (start of "explicit=yes")
%?if(%ss(0,10,%iC),=,explicit=y)<%arExplicit|>
```

**Why `%iC` instead of `%ik`?**
Testing on iPod Classic 7G revealed that `%ik` (grouping) does not reliably trigger WPS conditionals, even when the tag is correctly written. The `%iC` (comment) approach is proven by the `adwaitapod` theme, which ships with Rockbox and uses this exact pattern.

**Why check 10 characters?**
- `explicit=yes` starts with `explicit=y` (10 chars)
- `explicit=no` starts with `explicit=n` (10 chars)
- Checking 10 chars distinguishes between yes and no
- The `adwaitapod` theme checks 8 chars (`explicit`) but can't distinguish yes/no

#### Dynamic Title Width

To prevent the badge from overlapping scrolling titles, two conditional viewports are used:

```
# Wide viewport (clean tracks) — renders only when NOT explicit
%V(18,-82,-20,22,8)
%?if(%ss(0,10,%iC),=,explicit=y)<|%s%al%?it<%it|%fn>>

# Narrow viewport (explicit tracks) — renders only when explicit
%V(18,-82,-80,22,8)
%?if(%ss(0,10,%iC),=,explicit=y)<%s%al%?it<%it|%fn>|>

# Badge viewport — renders only when explicit
%V(-72,-82,52,16,3)
%?if(%ss(0,10,%iC),=,explicit=y)<%arExplicit|>
```

The key insight: Rockbox renders ALL viewports, but conditional content (`%?if`) controls what appears. The wide and narrow viewports occupy overlapping screen space, but only one has visible content at a time.

## Data Flow

```
1. User runs: python3 explicit_tagger.py /Music
                    |
2. Script reads:    FLAC → artist="Lil Nas X", title="MONTERO"
                    |
3. Deezer lookup:   GET api.deezer.com/search?q=... → explicit_lyrics: true
                    |
4. YT Music:        yt.search("Lil Nas X MONTERO") → isExplicit: True
                    |
5. Consensus:       Both agree → EXPLICIT
                    |
6. Write tags:      COMMENT = "explicit=yes; [existing comment]"
                    GROUPING = "EXPLICIT"
                    |
7. Sync to player:  Copy files + tagnavi_custom.config + patched WPS
                    |
8. Rebuild DB:      Settings > General > Database > Initialize Now
                    |
9. Result:          Database shows filtered views
                    Now Playing shows red "Explicit" badge
```

## Design Decisions

### Why modify file tags instead of using a sidecar database?
Rockbox's database engine (`tagcache`) only indexes tags embedded in audio files. There's no mechanism to load external metadata at runtime. Modifying the comment tag is the only way to get data into Rockbox's filtering and display systems.

### Why prepend instead of append to the comment field?
Rockbox's WPS `%ss(start, length, string)` function extracts a substring by position. Prepending ensures the explicit marker is always at position 0, making the WPS conditional reliable regardless of what other content exists in the comment field.

### Why use lowercase `explicit=yes` instead of `EXPLICIT=YES`?
The `adwaitapod` theme (shipped with Rockbox) established the convention of lowercase `explicit` in its WPS conditional. Following this convention ensures compatibility with existing theme implementations and community expectations.

### Why Deezer as primary API instead of Spotify?
Spotify requires OAuth app registration (user must create a developer account). Deezer's search API requires zero authentication — the script works out of the box with no setup. For a tool meant to be shared with the community, zero-friction setup was prioritized.

### Why not use a Rockbox plugin?
Rockbox plugins run on the player hardware (ARM processor, limited memory). Network access is not available on most targets. The detection must happen on a computer with internet access, making an offline tagging approach the only viable option.

## Limitations

1. **No runtime detection** — Files must be pre-tagged on a computer. Rockbox cannot query APIs.
2. **Comment field conflicts** — If other tools overwrite the comment field, explicit markers are lost. Re-running the tagger fixes this.
3. **API accuracy** — Deezer/YouTube Music may disagree with other sources. Some tracks may be misclassified.
4. **Theme-specific badges** — Each WPS theme must be individually patched. There's no universal overlay system in Rockbox.
5. **FLAC/MP3 only** — M4A, OGG, and other formats are not yet supported by the tagger.
