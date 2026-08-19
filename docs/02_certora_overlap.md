# 02 — Certora Hub FV Overlap

## Certora coverage (March 2026)

Certora formally verified the Aave V4 Hub contract.  Key properties:

| ID | Property | Status |
|----|----------|--------|
| P-01 | `draw` preserves global share accounting | Verified |
| P-05 | `restore` preserves global share accounting | Verified |
| P-06 | `reportDeficit` preserves global share accounting | Verified |
| P-08 | `eliminateDeficit` preserves global share accounting | Verified |
| M-01 | Interest accrual monotonicity | Fixed & verified |
| M-02 | Deficit non-negativity | Fixed & verified |
| L-01 … L-03 | Edge-case rounding bounds | Fixed & verified |

## This harness

Our Python model confirms the same accounting invariants (INV-1, INV-2, INV-4)
on the **model-level** representation of the same transitions.

- **Not** a replacement for Certora FV.
- **Not** claiming to find bugs Certora missed.
- **Is** an independent, deterministic, seeded fuzz harness that reaches
  ~184 000 state transitions with zero invariant violations.

## Divergence

Where Certora proves properties for **all** possible inputs, this harness
samples a seeded, bounded space (including dust-heavy boundary sweeps).  The
value is in rapid CI regression and educational clarity, not exhaustive proof.
