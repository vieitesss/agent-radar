# Detection by working-spinner match, not screen-hash change-detection

The poller decides "working vs stopped" by matching the live braille working
spinner in each pane's `capture-pane` output (`detect_working`, pattern
`@agent-radar-working-pattern`, default the U+2800–U+28FF glyph), **not** by
hashing the captured screen and watching for change — which is what the original
charting (map.md, ticket 002/003) settled on.

## Why the pivot

Change-detection has two failure modes that screen content doesn't:

- **False negatives while working.** An agent can animate a spinner in place
  without the *hashed* region changing enough, or pause mid-thought; a pure
  screen-hash then reads "unchanged = stopped" and false-fires.
- **False positives from prose.** A transcript that merely quotes `Working...`
  or `esc to interrupt` looks like activity to a text-hint approach.

The braille spinner glyph only exists while the harness animates it, so it is a
precise positive signal for "working" and can't collide with quoted transcript
text. Matched byte-wise under `LC_ALL=C` (E2 A0–A3), it's locale-proof.

## Cost and the calibration knob

This is harness-specific: an agent whose busy indicator isn't a braille spinner
won't be detected. That's the physical-world tuning knob, kept as
`@agent-radar-working-pattern` — override it with the harness's own marker.
pi/claude/codex/opencode all animate the braille spinner out of the box.

## Status of the original decision

Supersedes the change-detection mechanism in ticket 002 ("hashes captured agent
panes") and the hashing assumption in ticket 003. The state store no longer
carries a `HASH` key. Everything else in those tickets (one global idle
threshold, `STATE=stopped` + `STOPPED_AT`, one toast per transition) stands.
