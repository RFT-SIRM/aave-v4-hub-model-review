# Aave V4 Hub — model-level drawn/deficit ledger review (RFT-SIRM)

> Complementary to Certora Hub FV.  **No novel Class A/B finding.**

[![harness](https://github.com/RFT-SIRM/aave-v4-hub-model-review/actions/workflows/ci.yml/badge.svg)](https://github.com/RFT-SIRM/aave-v4-hub-model-review/actions/workflows/ci.yml)

---

## Quick start

```bash
python3 poc_hub_state_machine.py
```

Requires Python 3.10+; standard library only.

---

## What this is

A deterministic, seeded Python state machine that simulates the Aave V4 **Hub**
drawn / deficit ledger transitions (`draw`, `restore`, `reportDeficit`,
`eliminateDeficit`).  It checks four invariants after every transition and runs
184 000 operations (seeded + boundary sweep) with **zero violations**.

- Exact on-chain interest accrual (`calculateLinearInterest` from `MathUtils.sol`).
- RAY-precision arithmetic (`ray_mul_up/down`, `ray_div_up/down`).
- Boundary matrix B-1 … B-5 for edge-case confirmation.

## What this is not

- Not a bytecode audit.
- Not a full protocol simulation (premium, dual-ledger, add/remove/sweep are
  out of scope — see [00_scope.md](docs/00_scope.md)).
- Not a claim of bugs missed by Certora Hub FV.

---

## Results

| Metric | Value |
|--------|-------|
| Total operations | **184 000** |
| Invariant violations | **0** |
| R-01 dust events | 9 564 |
| R-02 liquidity checks passed | 63 050 |

See [05_harness_spec.md](docs/05_harness_spec.md) for full configuration and
boundary matrix.

---

## Design notes

- **R-01** — `draw`/`restore` pair at fixed index can leave 0–1 share residual
  (expected rounding, not a vulnerability).
- **R-02** — `reportDeficit` does not change liquidity (correct by design, noted
  for integrators).

---

## Document map

| File | Content |
|------|---------|
| [docs/00_scope.md](docs/00_scope.md) | Scope, known model gaps, Certora relation |
| [docs/01_architecture.md](docs/01_architecture.md) | Hub ledger model, transitions, rounding discipline |
| [docs/02_certora_overlap.md](docs/02_certora_overlap.md) | Certora FV overlap and divergence |
| [docs/03_invariant_catalogue.md](docs/03_invariant_catalogue.md) | INV-1 … INV-4, R-01, R-02 |
| [docs/04_findings.md](docs/04_findings.md) | Findings summary (0 novel Class A/B) |
| [docs/05_harness_spec.md](docs/05_harness_spec.md) | Harness configuration, results, CI |
| [docs/TECHNICAL_MEMO.md](docs/TECHNICAL_MEMO.md) | Full technical memo |

---

## Lab

UltraCore RFT (RFT-SIRM): https://github.com/RFT-SIRM/UltraCore-RFT

## License

_Copyright 2026 Eugeny (RFT-SIRM). Licensed under [Apache 2.0](LICENSE)._
