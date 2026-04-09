# Theme Patches

This directory contains WPS theme patches that add the "Explicit" badge to popular Rockbox themes.

## Available Patches

| Theme | Author | Status |
|-------|--------|--------|
| Nightpod | Christian Soffke | Tested on iPod Classic 7G |

## How Theme Patches Work

Each patch adds three elements to a WPS theme file:

1. **Wide title viewport** — Full-width scrolling title for clean tracks
2. **Narrow title viewport** — Shortened title for explicit tracks (makes room for badge)
3. **Explicit badge viewport** — Red "Explicit" text, right-aligned on the title line

### The Core WPS Code

```
# Wide title (clean tracks only)
%V(18,-82,-20,22,8)
%Vf(ffffff)
%Vb(080808)
%?if(%ss(0,10,%iC),=,explicit=y)<|%s%al%?it<%it|%fn>>

# Narrow title (explicit tracks only)
%V(18,-82,-80,22,8)
%Vf(ffffff)
%Vb(080808)
%?if(%ss(0,10,%iC),=,explicit=y)<%s%al%?it<%it|%fn>|>

# Explicit badge
%V(-72,-82,52,16,3)
%Vf(ff0000)
%Vb(080808)
%?if(%ss(0,10,%iC),=,explicit=y)<%arExplicit|>
```

### Adapting for Other Themes

To add the Explicit badge to any theme:

1. **Find the title viewport** — Look for `%it` (track title tag) in the WPS file
2. **Note the viewport coordinates** — The `%V(x, y, width, height, font)` line above it
3. **Duplicate the viewport** — Create a wide (original) and narrow (reduced right margin) version
4. **Add conditionals** — Wrap each in `%?if(%ss(0,10,%iC),=,explicit=y)` with opposite logic
5. **Add the badge viewport** — Position it in the space freed by the narrow title

### Key Parameters to Adjust

| Parameter | What to change | How to find it |
|-----------|---------------|----------------|
| `y` position | Match the title's y coordinate | Copy from original title viewport |
| Font slot | Use a smaller font than the title | Check `%Fl()` declarations at top of WPS |
| Colors | Match theme's accent color scheme | Check `%Vf()` (foreground) values |
| Background | Match theme's background color | Check `%Vb()` values |
| Width | Adjust badge width for font size | Test on device, 50-60px typical |

## Contributing Theme Patches

If you create a patch for a theme not listed here:

1. Test it on real hardware (or the Rockbox simulator)
2. Note which Rockbox targets you tested on
3. Submit a pull request with the patched WPS and a screenshot
