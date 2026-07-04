# agent-radar

A self-contained tmux plugin that surfaces every running coding agent, tells you
the moment one stops needing to work, and jumps you to the exact pane it lives in.

## Language

**Agent pane**:
A tmux pane whose foreground process is an allowlisted coding-agent executable
(`pi`, `claude`, `codex`, …). The unit agent-radar tracks and navigates to.
_Avoid_: session, window (an agent lives in a specific pane, not a whole session)

**Target**:
The fully-qualified `session:window.pane` address of an agent pane — what the
navigator jumps to and what agents are sorted by alphabetically.
_Avoid_: location, path

**Working**:
An agent pane visibly animating its busy spinner. The only positive signal;
everything else is "not working".
_Avoid_: busy, active

**Stopped**:
An agent pane that has shown no working spinner for the idle threshold. Means
"go look" — indistinguishable from, and treated the same as, "waiting for input".
_Avoid_: idle, done, finished

**Unseen-stopped**:
A stopped agent you have not focused since it stopped. The top-priority tier in
the navigator (red dot) — the agents that actually need you.

**Seen-stopped**:
A stopped agent whose session you focused after it stopped, marking it handled.
The bottom tier in the navigator (green dot).
_Avoid_: dismissed, acknowledged
