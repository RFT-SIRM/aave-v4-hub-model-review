# 00 — Scope & Known Model Gaps

## Covered surface

This repository contains a **model-level** Python state machine for the Aave V4
**Hub** drawn / deficit ledger.  The harness exercises four state transitions:

| Transition | Invariant checks |
|------------|------------------|
| `draw`     | INV-1, INV-3, INV-4 |
| `restore`  | INV-1, INV-2, INV-3, INV-4, R-01, R-02 |
| `reportDeficit` | INV-1, INV-2, INV-3, INV-4, R-02 |
| `eliminateDeficit` | INV-1, INV-2, INV-3, INV-4 |

## Known model gaps (not exercised)

1. **Premium delta** — `_applyPremiumDelta` / `Premium.calculatePremiumRay`
   signed-offset dynamics are fixed to zero throughout the harness.
2. **eliminateDeficit pricing** — the real on-chain price is
   `toAddedSharesUp(totalAddedAssets() / addedShares)`; the model uses a
   constant 1:1 added-share burn price.
3. **Add / remove / sweep / reclaim / fee-minting** — not modeled; liquidity is
   treated as an abundant external pool.
4. **Live interest-rate recomputation** — a constant drawn rate per run is used.
   Accrual itself uses the exact on-chain `calculateLinearInterest` formula
   (`MathUtils.sol`), not an approximation.
5. **Single asset, multiple spokes** — cross-asset interactions are out of scope.
6. **Spoke dual-ledger** (IC-04) — noted as a Proposal; not tested by this harness.

## What this is / is not

- **Is:** a deterministic, seeded, boundary-fuzzed model harness that confirms
  invariants on the covered surface.
- **Is not:** a bytecode audit, a full protocol simulation, or a source of novel
  Class A / B security findings.

## Relation to Certora Hub FV (March 2026)

Certora formally verified the Hub contract (P-01, P-05, P-06, P-08; M-01 … L-03
fixed).  This harness is **complementary** — it confirms the same invariants at
model level with a different toolchain (Python / property-based fuzz).
