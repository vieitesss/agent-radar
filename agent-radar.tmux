#!/usr/bin/env sh
set -eu

current_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P) || exit 0

# Options:
#   @agent-radar-key=a
#   @agent-radar-popup-width=40%
#   @agent-radar-popup-height=30%
#   @agent-radar-popup-position=C (or x,y; corners: top-left/tl, top-right/tr, bottom-left/bl, bottom-right/br)
opt() {
    v=$(tmux show-option -gqv "$1" 2>/dev/null || true)
    [ -n "$v" ] && printf '%s' "$v" || printf '%s' "$2"
}

status_cmd="#($current_dir/scripts/agent-radar-status '#S')"
status_left=$(tmux show-option -gqv status-left 2>/dev/null || true)

case "$status_left" in
    *agent-radar-status*) ;;
    *) tmux set-option -g status-left "${status_left}${status_cmd} " ;;
esac

ensure_window_format() {
    name=$1
    marker='#{?@agent-radar-window-stopped,#[bg=#{@agent-radar-window-color}],}'
    fmt=$(tmux show-option -gqv "$name" 2>/dev/null || true)
    case "$fmt" in
        *agent-radar-window-stopped*) ;;
        *) tmux set-option -g "$name" "${marker}${fmt}#[default]" ;;
    esac
}

tmux set-option -gq @agent-radar-window-color "$(opt @agent-radar-window-color red)"
ensure_window_format window-status-format
ensure_window_format window-status-current-format

tmux set-option -gq @agent-radar-plugin-dir "$current_dir"

popup_key=$(opt @agent-radar-key a)
popup_width=$(opt @agent-radar-popup-width '40%')
popup_height=$(opt @agent-radar-popup-height '30%')
popup_position=$(opt @agent-radar-popup-position C)
popup_x=C
popup_y=C
case "$popup_position" in
    top-left|tl) popup_x=0; popup_y=0 ;;
    top-right|tr) popup_x=R; popup_y=0 ;;
    bottom-left|bl) popup_x=0; popup_y=P ;;
    bottom-right|br) popup_x=R; popup_y=P ;;
    *,*) popup_x=${popup_position%%,*}; popup_y=${popup_position#*,} ;;
    *) popup_x=$popup_position; popup_y=$popup_position ;;
esac

tmux bind-key "$popup_key" display-popup -E -e TERM=tmux-256color -w "$popup_width" -h "$popup_height" -x "$popup_x" -y "$popup_y" -d "#{pane_current_path}" "$current_dir/scripts/agent-radar-list"
tmux run-shell -b "$current_dir/scripts/agent-radar-poller start"
