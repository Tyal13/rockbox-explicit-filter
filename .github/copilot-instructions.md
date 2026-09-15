# Copilot Instructions

These rules are non-negotiable. They apply to code, comments, commit messages,
config, YAML, JSON, file paths, documentation, and chat responses.

## 1. ASCII punctuation only

Never emit non-ASCII punctuation. Specifically banned:

- em dash and en dash. Use `-`, `--`, a comma, a colon, or a new sentence.
- curly quotes. Use `"` and `'`.
- the single-character ellipsis. Use three periods.
- non-breaking spaces, and any other non-ASCII whitespace.

Reason: non-ASCII punctuation breaks PowerShell parsing in non-UTF-8 shells
(it encodes as mojibake) and it reads as machine-generated text.

Non-ASCII characters ARE allowed inside string literals when the code is
genuinely about internationalization, and in test fixtures that exist to
exercise Unicode handling. Everywhere else, ASCII.

## 2. Never put `#` in a filename

Obsidian and many tools parse `#` as a section anchor, so `Meeting #2.mov`
resolves as "the file Meeting, section 2.mov" and the reference silently
breaks. Also avoid `?`, `*`, `:`, `<`, `>`, `|`, `"`, `\`, and `/` in filenames.
Prefer lowercase-with-dashes.

## 3. Shell commands in documentation

- Plain code fences. Do not label a fence with a shell name.
- One command per line.
- No backslash line continuations, and no leading `$` or `#` prompt markers.

A reader should be able to select the block and paste it as-is.

## 4. Dates and times

ISO 8601. `2026-09-09`, or `2026-09-09T14:30:00Z` when time matters.
Never write a relative date ("last Tuesday", "next month") into a file that
will be read later. Resolve it to an absolute date.

## 5. Output style

Be terse. Lead with the answer. Skip preamble, skip restating the question,
skip summarizing what you just did unless asked. Technical jargon is fine
without a gloss. If something is uncertain, say so in one line rather than
hedging throughout.

## 6. Do not invent values

Never fill a required field with a plausible-looking guess: no invented dates,
version numbers, metrics, IDs, or citations. If a value is unknown, leave a
literal `TODO` and say what is missing.
