#!/usr/bin/env sh
# shellcheck shell=sh disable=SC1007
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

# --- Glance setup on source/re-source ---
glance=$(opt @agent-radar-glance on)
glance_row=$(opt @agent-radar-glance-row 2)
case "$glance_row" in
    ''|*[!0-9]*) glance_row=2 ;;
esac
glance_idx=$((glance_row - 1))
glance_format="#('$current_dir/scripts/agent-radar-glance' '#{session_name}' '#{window_width}')"
. "$current_dir/scripts/agent-radar-glance-row"

if [ "$glance" = on ]; then
    current_slot=$(tmux show-option -gqv "status-format[$glance_idx]" 2>/dev/null || true)
    if agent_radar_glance_row_free "$glance_idx" "$current_slot"; then
        agent_radar_glance_row_claim "$glance_idx" "$current_slot"

        current_status=$(tmux show-option -gqv status 2>/dev/null || true)
        orig_status=$(tmux show-option -gqv @agent-radar-glance-orig-status 2>/dev/null || true)
        if [ "$current_slot" != "$glance_format" ] || [ -z "$orig_status" ]; then
            tmux set-option -gq @agent-radar-glance-orig-status "$current_status"
        fi
        case "$current_status" in
            on|1)
                tmux set-option -g status "$glance_row"
                ;;
            [0-9]*)
                if [ "$current_status" -lt "$glance_row" ] 2>/dev/null; then
                    tmux set-option -g status "$glance_row"
                fi
                ;;
        esac

        tmux set-option -gq @agent-radar-glance-state on
    else
        tmux display-message "agent-radar: status line $glance_row is in use; set -g @agent-radar-glance-row M"
    fi
else
    # Setting is off: teardown any live glance we previously installed.
    current_slot=$(tmux show-option -gqv "status-format[$glance_idx]" 2>/dev/null || true)
    case "$current_slot" in
        "$glance_format")
            agent_radar_glance_row_release "$glance_idx"

            current_status=$(tmux show-option -gqv status 2>/dev/null || true)
            orig_status=$(tmux show-option -gqv @agent-radar-glance-orig-status 2>/dev/null || true)
            if [ "$current_status" = "$glance_row" ]; then
                case "$orig_status" in
                    ''|on|1)
                        tmux set-option -g status on
                        ;;
                    [0-9]*)
                        if [ "$orig_status" -lt "$glance_row" ] 2>/dev/null; then
                            tmux set-option -g status "$orig_status"
                        fi
                        ;;
                esac
            fi
            ;;
    esac
    tmux set-option -gu @agent-radar-glance-state 2>/dev/null || true
fi

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

tmux bind-key "$popup_key" display-popup -E -e TERM=tmux-256color -w "$popup_width" -h "$popup_height" -x "$popup_x" -y "$popup_y" -d "#{pane_current_path}" "'$current_dir/scripts/agent-radar-list'"
tmux run-shell -b "'$current_dir/scripts/agent-radar-poller' start"

# --- Maintenance hook (seen-mark + window highlight) when glance is off ---
session_window_changed_hooks=$(tmux show-hooks -g session-window-changed 2>/dev/null || true)
case "$session_window_changed_hooks" in
    *agent-radar-status*) ;;
    *) tmux set-hook -ga session-window-changed "run-shell -b \"'$current_dir/scripts/agent-radar-status' '#{session_name}'\"" ;;
esac

# --- Toggle the glance line ---
tmux bind-key A run-shell -b "'$current_dir/scripts/agent-radar-toggle'"
