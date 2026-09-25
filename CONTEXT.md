# agent-radar

A self-contained tmux plugin that surfaces every running coding agent, tells you
the moment one stops needing to work, and jumps you to the exact pane it lives in.

## Language

**Agent pane**:
A tmux pane whose foreground process is an allowlisted coding-agent executable
(`pi`, `claude`, `codex`, `hermes`, …). The unit agent-radar tracks and
navigates to.
_Avoid_: session, window (an agent lives in a specific pane, not a whole session)

**Target**:
The fully-qualified `session:window.pane` address of an agent pane — what the
navigator jumps to and what agents are sorted by alphabetically.
_Avoid_: location, path

**Working indicator**:
The live marker a harness paints while working — a braille progress glyph
(pi/codex), Claude Code's spinner followed by its live status word, ellipsis,
and opening parenthesis (not its completed-turn summary), a pulsing square
progress bar (opencode), or the running hint on hermes' prompt line
(`msg=interrupt`). The one positive signal agent-radar keys off; it only exists
while the harness is working, so it can't be faked by quoted transcript text.
_Avoid_: harness-specific names as generic terms

**Working**:
An agent pane visibly animating its working indicator. The only positive signal;
everything else is "not working".
_Avoid_: busy, active

**Stopped**:
An agent pane that has shown no working indicator for the idle threshold. Means
"go look" — indistinguishable from, and treated the same as, "waiting for input".
_Avoid_: idle, done, finished

**Unseen-stopped**:
A stopped agent whose own pane you have not focused since it stopped. The
top-priority tier in the navigator (red dot) — the agents that actually need
you. Being elsewhere in its session (a different pane) does not clear it.

**Seen-stopped**:
A stopped agent whose exact pane you focused after it stopped, marking it
handled. The bottom tier in the navigator (green dot).
_Avoid_: dismissed, acknowledged

**Glance row**:
An always-visible tmux status row that lists every agent pane with its status
dot (red unseen-stopped, yellow working, green seen-stopped). The passive way to
watch agents.
_Avoid_: status line, second row, radar bar

**Navigator**:
The on-demand list of every agent pane, unseen-stopped first, that jumps to the
chosen target. The active way to reach an agent.
_Avoid_: popup, picker, switcher
