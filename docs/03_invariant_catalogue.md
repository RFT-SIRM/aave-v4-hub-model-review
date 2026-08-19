# 03 — Invariant Catalogue

All invariants are checked after **every** state transition in the harness.

## INV-1 — Global drawn-share conservation

```
asset.drawn_shares == Σ(spoke.drawn_shares for all spokes)
```

**Checked in:** `draw`, `restore`, `reportDeficit`, `eliminateDeficit`.

## INV-2 — Global deficit-ray conservation

```
asset.deficit_ray == Σ(spoke.deficit_ray for all spokes)
```

**Checked in:** `restore` (indirect), `reportDeficit`, `eliminateDeficit`.

## INV-3 — Non-negativity

All of the following must be ≥ 0:
- `asset.drawn_shares`
- `asset.deficit_ray`
- `asset.liquidity`
- `spoke.drawn_shares`
- `spoke.deficit_ray`
- `spoke.added_shares`

**Checked in:** all transitions.

## INV-4 — Index monotonicity

```
asset.drawn_index >= prev_drawn_index   (after accrual)
```

Interest accrual never decreases the index.  Equality holds when `dt == 0`
or `drawn_shares == 0`.

**Checked in:** all transitions (compares against pre-transition index).

## R-01 — Rounding residual (design note, **not a vulnerability**)

When `draw(x)` and `restore(x)` occur at a **fixed** index (no interest between
them), the share mint uses `ray_div_up` while the burn uses `ray_div_down`.
This can leave a **0 or 1 share** residual on the spoke.

**Observation:** 9 564 dust events across 184 000 ops (all bounded to 0–1 shares).

## R-02 — Liquidity shape on deficit (design note, **not a vulnerability**)

`reportDeficit` burns drawn shares and creates deficit, but **does not touch**
`asset.liquidity`.  The protocol's invariant is that liquidity is unchanged
during a deficit report (the assets were already drawn).

**Observation:** 63 050 liquidity-shape checks passed (restore + reportDeficit).
