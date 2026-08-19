# 01 — Architecture

## Hub ledger model

The Aave V4 Hub maintains a **drawn** position and a **deficit** position per
asset.  Each asset has:

- `drawn_index` — interest accumulator (RAY = 1.0)
- `drawn_shares` — total shares outstanding at asset level
- `liquidity` — available assets in the Hub
- `deficit_ray` — total deficit (in ray-precise units)
- `drawn_rate` — per-second interest rate (ray)
- `spokes` — mapping `spoke_name → SpokeState`

Each `SpokeState` tracks:

- `drawn_shares` — shares drawn by this spoke
- `deficit_ray` — deficit attributed to this spoke
- `added_shares` — shares available for deficit elimination
- `halted` / `active` — lifecycle flags

## Interest accrual

`accrue(asset, now)` updates `drawn_index` using the exact Solidity formula:

`SECONDS_PER_YEAR = 365 * 86400`.

## State transitions

### draw(spoke, amount, now)
1. `accrue`
2. `shares = ray_div_up(amount, drawn_index)`
3. Mint shares to asset and spoke; decrease liquidity.

### restore(spoke, drawn_amount, now)
1. `accrue`
2. `shares = ray_div_down(drawn_amount, drawn_index)`
3. Burn shares from asset and spoke; increase liquidity.

### reportDeficit(spoke, drawn_amount, now)
1. `accrue`
2. `shares = ray_div_down(drawn_amount, drawn_index)`
3. Burn drawn shares; move the same value into `deficit_ray` (asset + spoke).
4. Liquidity is **not** changed (R-02).

### eliminateDeficit(caller, covered, amount, now)
1. `accrue`
2. Compute `deficit_amount_ray` (capped at spoke deficit).
3. `deficit_to_eliminate = from_ray_up(deficit_amount_ray)` — round up to whole units.
4. Burn `shares_burned = deficit_to_eliminate` from `caller.added_shares`.
5. Reduce `asset.deficit_ray` and `covered.deficit_ray` by `deficit_amount_ray`.

## Rounding discipline

- **Mint** (draw): `ray_div_up` — conservative for protocol.
- **Burn** (restore, reportDeficit): `ray_div_down` — conservative for protocol.
- **Deficit elimination**: `from_ray_up` — ensures full coverage of the ray-precise deficit.
