# 05 — Harness Specification

## File

`poc_hub_state_machine.py` — Python 3.10+ standard library only.

## Entry point

```bash
python3 poc_hub_state_machine.py
```

## Configuration

### Seeded runs (deterministic)

| Seed | Spokes | Ops | Rate | Dust-heavy |
|------|--------|-----|------|------------|
| 1337 | 4 | 5 000 | 5.00 %/yr | No |
| 2024 | 8 | 8 000 | 2.00 %/yr | No |
| 9001 | 2 | 3 000 | 10.00 %/yr | No |
| 4242 | 3 | 8 000 | 1.00 %/yr | No |

### Boundary-sweep run

- 200 seeds × 800 ops = 160 000 ops
- 3 spokes, 1 000 bps/yr, dust-heavy (1–3 wei amounts)

## Results (last run)

- **Total operations:** 184 000
- **Invariant violations:** 0
- **R-01 dust events:** 9 564
- **R-02 liquidity-shape checks passed:** 63 050

## Boundary matrix

| Case | Scenario | Result |
|------|----------|--------|
| B-1 | draw(1)/restore(1) at index==RAY | PASS (0 residual) |
| B-2 | draw(1e6)/restore(1e6) at fixed moved index | R-01 reproduced (1 share residual) |
| B-3 | reportDeficit(1e6) after draw(1e6) | R-02 confirmed (liquidity untouched) |
| B-4 | restore(1 wei) at ~2× index | 0 shares (dust floor) |
| B-5 | multi-spoke eliminateDeficit partial+full | INV-2 held, s0 deficit zeroed |

## CI

GitHub Actions workflow in `.github/workflows/ci.yml`:

1. `py_compile` — syntax check.
2. `python3 poc_hub_state_machine.py` — run harness.
3. `grep -q "ALL INVARIANTS HELD"` — assert green.

## Determinism

All randomness uses `random.Random(seed)` with fixed seeds.  Re-running with the
same seed produces identical state traces and identical counts.
