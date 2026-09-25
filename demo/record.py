#!/usr/bin/env python3
"""Record a scripted agent-radar demo into demo.cast (asciicast v2 + markers).

Starts an isolated tmux server (-L ardemo) that loads the plugin from PLUGIN,
spawns fake agents, attaches one client in a pty, and plays TIMELINE against
it. Client output goes to the cast as "o" events; captions ("c") and desktop
notifications ("n", captured by a notify-send stub) are recorded as extra
event types for render.py.
"""
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import codecs
import fcntl
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
WORK = os.path.join(HERE, "work")
COLS, ROWS = 140, 28
SOCK = "ardemo"
PREFIX = "\x02"
HOME = os.path.join(WORK, "home")
ENV = dict(os.environ, HOME=HOME, PATH=f"{WORK}/bin:{os.path.expanduser('~/.fzf/bin')}:{os.environ['PATH']}",
           TERM="xterm-256color", LANG="C.UTF-8", LC_ALL="C.UTF-8", PS1="\\[\\e[38;5;111m\\]\\w\\[\\e[0m\\] $ ")
ENV.pop("TMUX", None)
ENV.pop("TMUX_PANE", None)
ENV["TMPDIR"] = os.path.join(WORK, "tmp")  # keep the plugin's mktemp files out of /tmp

AGENTS = {
    # name: (session, window, harness, repo, branch, tasks)
    "auth": ("api", "auth", "claude", "api", "feat/limits", [
        {"prompt": "add rate limiting to POST /login",
         "steps": ["Read src/auth/login.ts", "Edit src/auth/limiter.ts", "Run npm test -- auth"],
         "reply": "Added a token-bucket limiter to POST /login plus 3 tests. All green."},
    ]),
    "migrate": ("api", "db", "codex", "api", "feat/limits", [
        {"prompt": "write the migration for the attempts table",
         "steps": ["Read db/schema.sql", "Create db/migrations/0042_login_attempts.sql", "Run make migrate"],
         "reply": "Migration 0042 applied locally; rollback tested."},
    ]),
    "navbar": ("web", "ui", "pi", "web", "fix/navbar", [
        {"prompt": "the mobile navbar overlaps the hero, fix it",
         "steps": ["Read src/components/Navbar.tsx", "Edit src/styles/navbar.css", "Run pnpm test navbar"],
         "reply": "Navbar is sticky with a spacer now; snapshot tests updated."},
        {"steps": ["Run git push -u origin fix/navbar", "Run gh pr create --fill"],
         "reply": "Opened PR #128."},
    ]),
    "docs": ("docs", "site", "claude", "docs", "main", [
        {"prompt": "document the new rate limit headers",
         "steps": ["Read api/openapi.yaml", "Edit docs/api/limits.md", "Edit docs/api/errors.md", "Run mkdocs build"],
         "reply": "Documented Retry-After and X-RateLimit-* headers."},
    ]),
}

# (seconds from start, action, arg)
TIMELINE = [
    (0.0, "caption", "Four coding agents are working in three tmux sessions"),
    (4.5, "caption", "The glance row shows every agent: yellow means working"),
    (9.0, "release", "migrate"),
    (9.5, "caption", "An agent stops: its dot turns red, you get a notification, and its window is highlighted"),
    (17.0, "caption", "prefix + a opens the navigator, with stopped agents listed first"),
    (17.5, "keys", PREFIX + "a"),
    (21.5, "keys", "\r"),
    (23.0, "expect", "api:db"),
    (22.0, "caption", "Enter jumps to the exact pane; once you see it, the dot turns green"),
    (27.0, "release", "auth"),
    (27.3, "release", "navbar"),
    (27.5, "caption", "Agents in other sessions and windows are tracked too"),
    (33.0, "caption", "Type in the navigator to filter, then jump across sessions"),
    (33.5, "keys", PREFIX + "a"),
    (35.0, "type", "navbar"),
    (37.5, "keys", "\r"),
    (38.3, "expect", "web:ui"),
    (38.5, "caption", "Reply to the agent and it is back to work (yellow)"),
    (39.5, "type", "looks good, open a PR"),
    (42.0, "keys", "\r"),
    (45.0, "caption", "prefix + A toggles the glance row"),
    (46.0, "keys", PREFIX + "A"),
    (48.5, "keys", PREFIX + "A"),
    (51.0, "release", "docs"),
    (51.2, "caption", "agent-radar · see every agent, know when it stops, jump right to it"),
    (57.0, "end", None),
]


def tmux(*args, check=True):
    return subprocess.run(["tmux", "-L", SOCK, *args], check=check, env=ENV,
                          capture_output=True, text=True).stdout


def sh(cmd, cwd=None):
    subprocess.run(cmd, shell=True, check=True, cwd=cwd, env=ENV, stdout=subprocess.DEVNULL)


def setup():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(f"{WORK}/ctl")
    os.makedirs(f"{WORK}/tasks")
    os.makedirs(f"{WORK}/tmp")
    bindir = f"{WORK}/bin"
    os.makedirs(bindir)
    # notify-send stub: log notifications instead of hitting a (missing) desktop.
    with open(f"{bindir}/notify-send", "w") as f:
        f.write(f"#!/bin/sh\nprintf '%s\\t%s\\n' \"$1\" \"$2\" >> '{WORK}/notify.log'\n")
    os.chmod(f"{bindir}/notify-send", 0o755)
    for h in ("claude", "pi", "codex"):
        os.symlink(f"{HERE}/bin/fake-agent", f"{bindir}/{h}")

    home = HOME
    os.makedirs(home)
    with open(f"{home}/.bashrc", "w") as f:
        f.write("PS1='\\[\\e[38;5;111m\\]\\w\\[\\e[0m\\] $ '\n")
    for repo, branch in {("api", "feat/limits"), ("web", "fix/navbar"), ("docs", "main")}:
        d = f"{home}/code/{repo}"
        os.makedirs(d)
        sh(f"git init -q -b main && git -c user.name=demo -c user.email=demo@x commit -q --allow-empty -m init"
           f" && git checkout -q -B {branch}", cwd=d)

    with open(f"{WORK}/tmux.conf", "w") as f:
        f.write(f"""
set -g default-terminal tmux-256color
set -ga terminal-overrides ',xterm-256color:RGB'
set -g default-shell /bin/bash
set -g base-index 1
set -g status-interval 1
set -g escape-time 0
set -g status-style 'bg=#181825,fg=#cdd6f4'
set -g status-left '#[bg=#89b4fa,fg=#1e1e2e,bold] #S #[default] '
set -g status-left-length 20
set -g status-right '#[fg=#6c7086]%H:%M '
set -g window-status-format ' #I:#W '
set -g window-status-current-format '#[bg=#313244,fg=#f5e0dc,bold] #I:#W '
set -g pane-border-style 'fg=#313244'
set -g pane-active-border-style 'fg=#89b4fa'
set -g popup-border-style 'fg=#89b4fa'
set -g popup-border-lines rounded
set -g message-style 'bg=#313244,fg=#cdd6f4'
set -g @agent-radar-idle-seconds 2
set -g @agent-radar-poll-interval 1
set -g @agent-radar-glance-fields 'dot,harness,session,branch'
set -g @agent-radar-glance-tint '#313244'
set -g @agent-radar-window-color '#e64553'
set -g @agent-radar-popup-width 62%
set -g @agent-radar-popup-height 40%
run-shell {PLUGIN}/agent-radar.tmux
""")
    return home


def start_agents(home):
    first = {}
    for name, (session, window, harness, repo, _branch, tasks) in AGENTS.items():
        with open(f"{WORK}/tasks/{name}.json", "w") as f:
            json.dump(tasks, f)
        open(f"{WORK}/ctl/{name}", "w").write("0")
        cwd = f"{home}/code/{repo}"
        cmd = f"{WORK}/bin/{harness} {WORK}/ctl/{name} {WORK}/tasks/{name}.json"
        if session not in first:
            tmux("new-session", "-d", "-s", session, "-n", window, "-x", str(COLS), "-y", str(ROWS), "-c", cwd, cmd)
            first[session] = True
        else:
            tmux("new-window", "-d", "-t", f"{session}:", "-n", window, "-c", cwd, cmd)
    tmux("select-window", "-t", "api:auth")


def release(name):
    p = f"{WORK}/ctl/{name}"
    n = int(open(p).read() or 0)
    open(p, "w").write(str(n + 1))


def boot(plugin=None):
    """Start the demo server, agents and an attached client; return the client pty fd."""
    global PLUGIN
    PLUGIN = plugin or PLUGIN
    subprocess.run(["tmux", "-L", SOCK, "kill-server"], env=ENV, capture_output=True)
    while subprocess.run(["tmux", "-L", SOCK, "ls"], env=ENV, capture_output=True).returncode == 0:
        time.sleep(0.1)
    home = setup()
    # Start the server with the config, then the agents; give the poller a moment.
    tmux("-f", f"{WORK}/tmux.conf", "new-session", "-d", "-s", "bootstrap")
    start_agents(home)
    tmux("kill-session", "-t", "bootstrap")
    time.sleep(3)

    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe("tmux", ["tmux", "-L", SOCK, "attach", "-t", "api"], ENV)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
    os.kill(pid, signal.SIGWINCH)
    return fd


def main():
    fd = boot()
    events = []
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    t0 = time.time()
    notify_seen = 0
    queue = sorted(TIMELINE, key=lambda e: e[0])
    typing = []  # pending (time, char)
    done = False
    while not done:
        now = time.time() - t0
        r, _, _ = select.select([fd], [], [], 0.02)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            events.append([round(time.time() - t0, 4), "o", decoder.decode(data)])
        while typing and typing[0][0] <= now:
            os.write(fd, typing.pop(0)[1].encode())
        while queue and queue[0][0] <= now:
            _, action, arg = queue.pop(0)
            if action == "caption":
                events.append([round(now, 4), "c", arg])
            elif action == "keys":
                os.write(fd, arg.encode())
            elif action == "type":
                typing += [(now + i * 0.09, ch) for i, ch in enumerate(arg)]
                typing.sort()
            elif action == "release":
                release(arg)
            elif action == "expect":
                got = tmux("display-message", "-p", "#S:#W").strip()
                if got != arg:
                    print(f"WARNING at {now:.1f}s: expected {arg}, client is on {got}", file=sys.stderr)
            elif action == "end":
                done = True
        log = f"{WORK}/notify.log"
        if os.path.exists(log):
            lines = open(log).read().splitlines()
            for line in lines[notify_seen:]:
                events.append([round(now, 4), "n", line])
            notify_seen = len(lines)

    events.append([round(time.time() - t0, 4), "end", ""])
    tmux("kill-server", check=False)
    with open(os.path.join(HERE, "demo.cast"), "w") as f:
        f.write(json.dumps({"version": 2, "width": COLS, "height": ROWS}) + "\n")
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"recorded {len(events)} events, {events[-1][0]:.1f}s")


if __name__ == "__main__":
    main()
