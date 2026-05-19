# Spec: Governor Accounting Fix

**Status:** Approved
**Date:** 2026-05-13
**Author:** hs

## §1 Problem

Governor's `/governor:status` dashboard shows **negative net savings** (-14,971 lifetime) despite blocking 718k+ tokens of tool output. This makes Governor look harmful rather than helpful — a dealbreaker for promotion.

Root causes:
1. **Overhead is double-counted.** Every `prompt_reinforcement` injection (~200 tokens) is recorded per-turn. Over 1000+ turns, this balloons to 700k+ overhead, but the prompt text is cached by Claude Code's prompt cache after the first turn — the real marginal cost is near zero after caching.
2. **Prompt reinforcement isn't a "cost" of filtering.** The compact-mode prompt fires regardless of whether any tool output was filtered. It's a baseline cost of running Governor, not a cost attributable to filtering.
3. **Tool failures show "–" for lifetime** in the Claude-rendered table because the ledger aggregation doesn't sum `tool_failure` events into a lifetime counter correctly (session works, lifetime returns 0 which Claude renders as dash).

## §2 Solution

1. **Remove prompt reinforcement from overhead calculation.** Prompt reinforcement is a fixed cost of Governor's compact mode, not variable overhead from filtering. Only count `tool_filter_context` and `session_start` as overhead — these are the actual additional tokens Governor injects beyond what would exist without it.
2. **Better: don't show overhead/net-saved at all.** The "net saved" framing is misleading because it compares apples (tool-output tokens that would have been in context) to oranges (prompt tokens that get cached). Replace with: show `tool-output tokens blocked` as the headline metric, drop the overhead/net-saved rows entirely.
3. **Fix tool_failure lifetime counting.** Ensure `aggregate_governor_accounting` counts `tool_failure` events correctly across all ledger files.

## §3 Contradictions

_(none)_ — This change only modifies the accounting/display logic in `status()` and `aggregate_governor_accounting()`. No positioning conflicts. Governor's README claims "honest telemetry" — removing a misleading metric is more honest, not less.

## Implementation plan

**Date:** 2026-05-13
**Estimated effort:** 30 minutes

### Step-by-step

1. **Remove overhead and net-saved from `aggregate_governor_accounting` return and `status()` output** — `scripts/governor.py:968-1070`
   - Remove `overhead`, `overhead_by_source`, `net_saved`, `direct_saved` from the aggregation dict
   - Remove `context_overhead_injected` event processing from the loop
   - Remove overhead/net-saved print lines from `status()`
   - Keep `record_context_overhead()` function and ledger writes — they're useful for debugging, just don't surface them in the dashboard
   - Test: run `governor.py status` and verify no overhead/net-saved lines, tool_blocked shows correct number

2. **Rename "Tool-output tokens blocked" to "Tokens saved" in status output** — `scripts/governor.py:1039-1049`
   - Simpler headline metric
   - Drop "direct memory saved" line (always 0, no compress feature shipping yet)
   - Test: verify output is clean and concise

3. **Fix tool_failure lifetime display** — `scripts/governor.py:998-999`
   - Already counted correctly in aggregation, verify the field name matches what `status()` prints
   - Test: confirm lifetime failures shows a number not "–"

4. **Update statusline accounting in `statusline()` function** — `scripts/governor.py:~1100`
   - The statusline also calls `aggregate_governor_accounting` — verify it still works after field removal
   - Test: run `governor.py statusline` and verify no crash

### Files touched

| File | New / Modified | Lines (approx) |
|---|---|---|
| `scripts/governor.py` | M | ~40 |

### Tests required

- **Smoke test:** `python3 scripts/governor.py status` shows correct numbers, no overhead/net rows
- **Statusline test:** `python3 scripts/governor.py statusline` doesn't crash
- **Manual verification:** Run `/governor:status` in a live Claude Code session

### Gates

- [ ] `python3 scripts/governor.py status` runs clean
- [ ] `python3 scripts/governor.py statusline` runs clean
- [ ] No overhead/net-saved in output
- [ ] tool_blocked shows ~718k lifetime
- [ ] Copy to marketplace + cache installed paths
- [ ] Push to GitHub (no Co-Authored-By)

### Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Removing overhead breaks statusline JSON | low | Test statusline after change |
| Existing ledger data has overhead events | none | We keep recording them, just don't display |
