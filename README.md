# agent-radar

A self-contained tmux plugin that gives you the one herdr feature worth having
without leaving tmux: see every running coding agent, jump straight to the pane
it lives in, and get told the moment any agent stops needing you — for *any*
harness, not just the ones with hooks.

## What it does

- **Detects agent panes** — any tmux pane whose foreground process matches the
  allowlist (`pi,claude,codex,opencode,aider,cursor` by default).
- **Notices when an agent stops** — polls each agent pane and looks for the
  agent's live "working" spinner (the animated braille glyph pi/claude/codex
  show while busy). A pane is `working` while that spinner is on screen and
  flips to `stopped` when it's gone for N seconds. The spinner only exists
  while the agent animates it, so typing, editing, or even a transcript that
  quotes the words "Working..." can't be mistaken for a busy agent. "Done" and
  "waiting for input" both mean the same thing: go look.
- **Notifies you** — a macOS notification fires once per stop transition (via
  `osascript`), backed by a persistent status-left segment listing sessions
  with a stopped agent, dismissed when you focus that session.
- **Navigates** — `prefix + A` opens an fzf popup listing all agent panes,
  stopped ones first, with a green/yellow status dot and stopped age. Pick one
  and it jumps to that exact `session:window.pane`.

## Requirements

- `tmux`
- `fzf` (for the navigator popup)
- macOS for OS notifications (`osascript`); everything else is cross-platform.

## Install

Add to `~/.tmux.conf`:

```tmux
run-shell /path/to/tmux/plugins/agent-radar/agent-radar.tmux
```

In this repo it's installed via the OS manifest symlinks; the line above is
what a standalone install looks like. Reload tmux afterwards.

## Usage

- `prefix + A` — open the navigator popup, select an agent, jump to its pane.
- The status-left segment shows sessions with an unseen stopped agent, e.g.
  `[agents - work / build×2]`.

## Options

Set with `tmux set-option -g <name> <value>` (or `set -g` in `~/.tmux.conf`):

| Option | Default | Meaning |
|--------|---------|---------|
| `@agent-radar-processes` | `pi,claude,codex,opencode,aider,cursor` | Comma-separated agent executable names to detect |
| `@agent-radar-idle-seconds` | `3` | Seconds with no working indicator before a pane is "stopped" (the one calibration knob) |
| `@agent-radar-poll-interval` | `2` | Seconds between poll cycles |
| `@agent-radar-working-pattern` | braille spinner glyph | ERE for an agent's live "working" chrome, matched byte-wise; defaults to the braille spinner pi/claude/codex animate while busy. Override for agents that use a different indicator |
| `@agent-radar-key` | `A` | Prefix key that opens the navigator popup |
| `@agent-radar-popup-width` | `90%` | Popup width |
| `@agent-radar-popup-height` | `80%` | Popup height |
| `@agent-radar-popup-position` | `C` | Popup position: `C`, `x,y`, or corner shorthand (`tl`/`tr`/`bl`/`br`) |
| `@agent-radar-status-label` | `agents` | Label in the status segment |
| `@agent-radar-status-color` | `yellow` | Color of the status segment |

## How detection works

`agent-radar-poller` runs one tmux-scoped background daemon. Each cycle it
enumerates panes with `tmux list-panes -a`, keeps those whose TTY runs an
allowlisted agent, captures each pane and checks it against
`@agent-radar-working-pattern` for the live "working" spinner, and stores
per-pane state in tmux global environment (`TMUX_AGENT_RADAR_PANE_*`). A pane
goes `stopped` when it was working (armed) and then showed no spinner for
`@agent-radar-idle-seconds`. `agent-radar-status` reads that state for the
status segment; `agent-radar-list` reads it for the navigator.

## Scripts

- `agent-radar.tmux` — entry point: wires the status segment, keybind, and
  starts the poller.
- `scripts/agent-radar-poller` — the detection daemon (`start|once|stop|restart`).
- `scripts/agent-radar-status` — status-left segment for stopped agents.
- `scripts/agent-radar-list` — fzf navigator popup.
