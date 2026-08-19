# TECHNICAL MEMO — Aave V4 Hub Model Review

**Lab:** UltraCore RFT (RFT-SIRM)  
**Date:** 2026-08-19  
**Scope:** Aave V4 Hub drawn/deficit ledger — model-level invariant harness  
**Tooling:** Python 3.11, standard library only  

---

## Executive Summary

This memo documents a model-level state-machine review of the Aave V4 Hub
drawn / deficit ledger.  The harness (`poc_hub_state_machine.py`) simulates
`draw`, `restore`, `reportDeficit`, and `eliminateDeficit` transitions with
exact on-chain interest accrual (`calculateLinearInterest` from `MathUtils.sol`).

**Result:** 184 000 deterministic state transitions executed across seeded and
boundary-sweep configurations.  **Zero invariant violations.**

No novel Class A or Class B security finding is claimed.  Two design notes
(R-01, R-02) are documented as expected rounding and liquidity-shape behaviour.

---

## Method

1. **Model construction** — Python dataclasses mirror Hub `AssetState` and
   `SpokeState` with RAY-precision arithmetic.
2. **Invariant instrumentation** — INV-1 … INV-4 checked after every transition.
3. **Seeded fuzz** — 4 fixed configurations (2 400–8 000 ops each).
4. **Boundary sweep** — 200 seeds × 800 ops dust-heavy (1–3 wei amounts).
5. **Boundary matrix** — 5 explicit edge cases (B-1 … B-5).

---

## Quantitative Results

| Metric | Value |
|--------|-------|
| Total operations | **184 000** |
| draw | 5 652 |
| restore | 5 407 |
| reportDeficit | 4 250 |
| eliminateDeficit | 1 653 |
| R-01 dust events | **9 564** |
| R-02 liquidity checks passed | **63 050** |
| Expected-path reverts | 62 334 |
| Invariant violations | **0** |

---

## Design Notes

### R-01 — Rounding residual

`draw` mints with `ray_div_up`; `restore` burns with `ray_div_down`.  At a fixed
index this can leave 0–1 share on the spoke.  The harness confirms this is
bounded and deterministic (B-2).

### R-02 — Deficit liquidity shape

`reportDeficit` converts drawn shares to deficit without changing `liquidity`.
This is correct by design (liquidity exited at `draw` time) but noted for
integrators tracking liquidity deltas.

---

## Relation to Certora

Certora Hub FV (March 2026) formally verified P-01, P-05, P-06, P-08 and fixed
M-01 … L-03.  This harness is **complementary** — it confirms the same
invariants with an alternative toolchain (Python / deterministic fuzz) and
provides a lightweight CI regression target.

We do **not** claim to have found bugs that Certora missed.

---

## Known Gaps (Out of Scope)

1. Premium delta (`_applyPremiumDelta`) — fixed to zero.
2. `eliminateDeficit` pricing — simplified 1:1 burn; real price uses
   `toAddedSharesUp(totalAddedAssets() / addedShares)`.
3. Add / remove / sweep / reclaim / fee-minting — not modeled.
4. Live interest-rate strategy — constant rate per run.
5. Single asset only — no cross-asset logic.
6. Spoke dual-ledger (IC-04) — noted as Proposal, not tested.

---

## Conclusion

The covered surface of the Aave V4 Hub drawn/deficit ledger satisfies the
instrumented invariants across 184 000 model-level transitions.  No novel
security finding is reported.  The harness is suitable for CI regression and
educational reference.

**Label:** model-level, deterministic, boundary-seeded.  Not bytecode-level.
