# 04 — Findings

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| Novel Class A/B | **0** | No invariant violations detected. |
| Design notes | 2 | R-01, R-02 (documented, not vulnerabilities). |
| Proposals | 1 | IC-04 (Spoke dual-ledger, not tested). |

## R-01 — Rounding dust on draw/restore pair

**Type:** Design note  
**Status:** Expected behaviour  
**Detail:** `draw` uses `ray_div_up`; `restore` uses `ray_div_down`.  At a fixed
index this can strand 0–1 share.  The harness reproduces this in boundary case
B-2 and observes 9 564 such events across 184 000 operations.  All residuals are
bounded to {0, 1} shares.

## R-02 — Liquidity unchanged on reportDeficit

**Type:** Design note  
**Status:** Expected behaviour  
**Detail:** `reportDeficit` converts drawn shares to deficit without altering
`asset.liquidity`.  This is correct by protocol design (the liquidity left the
Hub at `draw` time), but noted for external integrations that track
liquidity deltas.

## IC-04 — Spoke dual-ledger (Proposal)

**Type:** Proposal / not tested  
**Status:** Out of scope for this harness  
**Detail:** The real Hub maintains both `SpokeData` (spoke-level aggregates) and
per-user `UserPosition` within each spoke.  Inconsistencies between these two
ledgers are not exercised by the model-level harness.  Recommended as a
follow-up with user-level fuzz or formal verification.

## Claim discipline

- We **do not** claim to have found a critical bug that Certora missed.
- We **do not** claim full equivalence to on-chain `eliminateDeficit` pricing
  (the model uses a simplified 1:1 added-share burn).
- We **do** confirm that the covered invariants hold across 184 000 deterministic
  transitions.
