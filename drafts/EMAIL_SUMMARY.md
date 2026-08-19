# DRAFT ONLY — Email summary (not for publication)

Subject: Aave V4 Hub model-level invariant harness — results & deliverables

Body:

---

Lab: UltraCore RFT (RFT-SIRM)
Repo: https://github.com/RFT-SIRM/aave-v4-hub-model-review

We have completed a model-level state-machine review of the Aave V4 Hub
drawn/deficit ledger.  The Python harness (stdlib only, deterministic, seeded)
executed 184 000 state transitions with zero invariant violations.

Key points:
- Complementary to Certora Hub FV (March 2026); not a replacement.
- No novel Class A/B finding claimed.
- Two design notes documented (R-01 rounding residual, R-02 liquidity shape).
- IC-04 (Spoke dual-ledger) noted as out-of-scope Proposal.
- CI workflow included; green on every push.

Full technical memo and invariant catalogue are in the repo docs/ directory.

---

*This file is a draft and not part of the published repository content.*
