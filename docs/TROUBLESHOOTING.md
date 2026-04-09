# Troubleshooting

## Common Issues

### "Explicit" badge not appearing on Now Playing screen

**Cause 1: Database not rebuilt**
After syncing tagged files, you must rebuild the database:
- Settings > General Settings > Database > Initialize Now
- Wait for rebuild to complete (1-2 minutes for large libraries)

**Cause 2: Theme not patched**
The "Explicit" badge requires a modified WPS theme file. Check that your `.rockbox/wps/YourTheme.wps` contains the explicit conditional:
```
%?if(%ss(0,10,%iC),=,explicit=y)<%arExplicit|>
```

**Cause 3: Comment tag not prepended**
Rockbox's WPS checks the FIRST characters of the comment. If `explicit=yes` is appended instead of prepended, the check fails. Re-run the tagger with `--force`:
```bash
python3 scripts/explicit_tagger.py /path/to/Music --force
```

**Cause 4: Using `%ik` instead of `%iC`**
The grouping tag (`%ik`) does not work reliably on all Rockbox targets. Always use the comment tag (`%iC`) with `%ss()`.

### Custom database views not appearing

**Cause 1: Missing config file**
Verify `tagnavi_custom.config` exists in `.rockbox/`:
```
/Volumes/YOURPLAYER/.rockbox/tagnavi_custom.config
```

**Cause 2: Database not rebuilt**
Custom views only appear after rebuilding the database with the config file in place.

**Cause 3: Syntax error in config**
Verify the file starts with the required header:
```
#! rockbox/tagbrowser/2.0
```

### Tagger reports "SKIP (no tags)" for files that have tags

**Cause: Tag key casing**
Some FLAC encoders write uppercase keys (`ARTIST`), others write lowercase (`artist`). The tagger handles both, but if you encounter this, run with `--force` to re-process.

### Tagger is slow

The tagger respects API rate limits:
- Deezer: ~0.2s per request
- YouTube Music: ~0.5s per request (only for explicit tracks or Deezer misses)

For a 7,000-track library, expect ~45-60 minutes. Subsequent runs skip already-tagged files and are much faster.

### Files show wrong explicit status

Re-run with `--force` to re-check all files:
```bash
python3 scripts/explicit_tagger.py /path/to/Music --force
```

Review the CSV report in `documentation/` to see what each API returned.

### Arr stack (Lidarr) re-downloading files

The tagger only modifies COMMENT and GROUPING tags. Lidarr should not detect this as a file change. If Lidarr is re-downloading, check if:
- Lidarr is configured to monitor file hashes (uncommon)
- Another tool is reverting the tag changes

### Theme looks broken after patching WPS

Restore the original theme file from your backup or re-download the theme. The WPS patch adds viewport definitions that may conflict with some themes' layouts. Adjust the viewport coordinates in the patch:

```
# Viewport format: %V(x, y, width, height, font)
# Adjust x and y to reposition the Explicit badge
%V(-72,-82,52,16,3)
```

## Getting Help

- [Rockbox Forums](https://forums.rockbox.org/) — Community support
- [Rockbox Wiki](https://www.rockbox.org/wiki/) — Official documentation
- [GitHub Issues](https://github.com/yourusername/rockbox-explicit-filter/issues) — Bug reports and feature requests
