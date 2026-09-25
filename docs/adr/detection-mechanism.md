# Detection by working-indicator match, not screen-hash change-detection

The poller decides "working vs stopped" by matching the live working indicator
in each pane's plain `capture-pane` output (`detect_working`, pattern
`@agent-radar-working-pattern`, default the U+2800–U+28FF braille glyph,
Claude Code's spinner + status word + ellipsis + opening parenthesis,
opencode's 4+-square progress bar, or hermes' prompt-line running hint
`msg=interrupt`), **not** by hashing the captured screen and watching for
change — which is what the original charting (map.md, ticket 002/003) settled
on.

## Why the pivot

Change-detection has two failure modes that screen content doesn't:

- **False negatives while working.** An agent can animate a working indicator in
  place without the *hashed* region changing enough, or pause mid-thought; a pure
  screen-hash then reads "unchanged = stopped" and false-fires.
- **False positives from prose.** A transcript that merely quotes `Working...`
  or `esc to interrupt` looks like activity to a text-hint approach.

These working markers are harness-specific. For Claude Code, the spinner alone
is not a working signal because completed-turn summaries reuse that glyph
family; the live status-line shape distinguishes an in-flight turn from those
summaries. Matched byte-wise under `LC_ALL=C`, the default is locale-proof.

## Cost and the calibration knob

This is harness-specific: an agent whose working indicator is neither braille,
Claude Code's live status-line shape, opencode's square bar, nor hermes'
prompt-line hint won't be detected. That's the physical-world tuning knob,
kept as `@agent-radar-working-pattern` — override it with the harness's own
marker. (hermes' hint is static rather than
animated, but the same trick applies: it exists only while a turn is in
flight, so it can't be faked by quoted transcript text — and it can't be
confused with hermes' always-present `⚕` branding, which shows up in both
working and idle states.)

## Status of the original decision

Supersedes the change-detection mechanism in ticket 002 ("hashes captured agent
panes") and the hashing assumption in ticket 003. The state store no longer
carries a `HASH` key. Everything else in those tickets (one global idle
threshold, `STATE=stopped` + `STOPPED_AT`, one toast per transition) stands.
