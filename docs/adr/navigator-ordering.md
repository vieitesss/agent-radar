# Navigator list ordered by seen-state tiers, not activity recency

The `agent-radar-list` popup orders agents into three seen-based tiers —
`unseen-stopped` (red) > `running` (yellow) > `seen-stopped` (green) — with the
unseen tier sorted oldest-first and the other two alphabetically by target.

A reader would reasonably expect a "recency" sort, and would be surprised that a
*running* agent outranks one that stopped ten minutes ago. The deliberate choice:
the list answers "who needs me?", and once you have focused a stopped agent's
session it is handled, so it drops below live work regardless of age. "Seen"
(focus-after-stopping, already tracked as `SEEN_STOPPED_AT` reaching
`STOPPED_AT`) measures the seen state directly, avoiding an arbitrary age
threshold and a list that reorders itself as the clock ticks. Oldest-first within
the unseen tier keeps long-neglected agents from rotting at the bottom.

Easy to reverse (pure sort logic in one awk block), recorded only because the
running-outranks-old-stopped behaviour looks wrong without this rationale.
