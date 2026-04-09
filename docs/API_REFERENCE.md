# API Reference

## Overview

The Rockbox Explicit Content Filter uses two free, zero-authentication music metadata APIs to determine whether tracks contain explicit content.

## Deezer Search API (Primary)

### Endpoint
```
GET https://api.deezer.com/search
```

### Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query. Supports `artist:"X" track:"Y"` syntax |
| `limit` | integer | Maximum results (default: 25, max: 100) |

### Example Request
```
GET https://api.deezer.com/search?q=artist:%22Lil%20Nas%20X%22%20track:%22MONTERO%22&limit=5
```

### Example Response
```json
{
  "data": [
    {
      "id": 1294198652,
      "title": "MONTERO (Call Me By Your Name)",
      "artist": {
        "id": 54aborting2149,
        "name": "Lil Nas X"
      },
      "album": {
        "title": "MONTERO"
      },
      "explicit_lyrics": true,
      "explicit_content_lyrics": 1,
      "explicit_content_cover": 0
    }
  ]
}
```

### Key Fields
| Field | Type | Description |
|-------|------|-------------|
| `explicit_lyrics` | boolean | `true` if track contains explicit content |
| `explicit_content_lyrics` | integer | 0=not explicit, 1=explicit, 2=unknown |
| `explicit_content_cover` | integer | 0=not explicit, 1=explicit |

### Authentication
None required.

### Rate Limits
- No official published limit
- Self-imposed: 0.2 seconds between requests (~300/minute)
- Deezer may throttle at higher rates

### Error Handling
- HTTP 200 with empty `data` array: track not found
- HTTP 429: rate limited (back off and retry)
- Network errors: retry up to 2 times with 1s delay

---

## YouTube Music API (Secondary)

### Library
```
pip install ytmusicapi
```

### Usage
```python
from ytmusicapi import YTMusic

yt = YTMusic()  # No authentication needed for search
results = yt.search("Lil Nas X MONTERO", filter="songs", limit=5)
```

### Example Response
```python
[
    {
        "title": "MONTERO (Call Me By Your Name)",
        "artists": [{"name": "Lil Nas X", "id": "UCmBA_wu8xGg1OfOkfW13Q0Q"}],
        "album": {"name": "MONTERO", "id": "MPREb_abc123"},
        "isExplicit": True,
        "duration_seconds": 137,
        "videoId": "6swmTBVI83k"
    }
]
```

### Key Fields
| Field | Type | Description |
|-------|------|-------------|
| `isExplicit` | boolean | `True` if track is marked explicit on YouTube Music |

### Authentication
None required for search operations. `YTMusic()` with no arguments uses unauthenticated mode.

### Rate Limits
- No official published limit
- Self-imposed: 0.5 seconds between requests
- Only queried when Deezer returns explicit=True (validation) or None (not found)

---

## Consensus Algorithm

```python
def determine_verdict(deezer_result, ytmusic_result):
    if deezer_result is True or ytmusic_result is True:
        return "explicit"
    elif deezer_result is False:
        return "clean"
    elif ytmusic_result is False:
        return "clean"
    else:
        return "unknown"
```

The algorithm errs on the side of flagging content as explicit. If either API says explicit, the track is marked explicit. A track is only marked clean if at least one API explicitly returns "not explicit."

## Accuracy Notes

- **Deezer** sources explicit flags from record label metadata. This is the same data used in streaming apps.
- **YouTube Music** may have slightly different classifications due to regional content policies.
- **Classical, jazz, and instrumental** music is almost always correctly classified as clean.
- **Non-English music** may have lower accuracy due to regional catalog differences.
- **Remixes and covers** may have different explicit status than originals.

## Privacy

Both APIs are queried over HTTPS. The only data sent is the artist name and track title — no personal information, no file contents, no listening history.
