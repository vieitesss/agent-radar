# Restart the poller daemon so it picks up script changes. Re-sourcing the
# plugin doesn't: `poller start` exits early while the old daemon is alive.
# Launched via run-shell so the daemon belongs to the tmux server, not this shell.
restart:
    tmux run-shell -b "'{{justfile_directory()}}/scripts/agent-radar-poller' restart"
