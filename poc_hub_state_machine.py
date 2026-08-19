#!/usr/bin/env python3
"""
poc_hub_state_machine.py
UltraCore RFT (RFT-SIRM) -- Aave V4 Hub model-level state machine + invariant harness.

Every number quoted anywhere in this pack's markdown (00/03/05/TECHNICAL_MEMO)
is the literal stdout of this file. Re-run it yourself:

    python3 poc_hub_state_machine.py

Python 3 standard library only. No network, no filesystem writes.

Scope / known model gaps (see 00_scope.md for the full list):
  - Premium delta fixed to 0 throughout (_applyPremiumDelta / Premium.
    calculatePremiumRay signed-offset dynamics are NOT exercised).
  - eliminateDeficit uses a constant 1:1 added-share burn price; the real
    toAddedSharesUp(totalAddedAssets()/addedShares) pricing is not modeled.
  - add/remove/sweep/reclaim/fee-minting are not modeled; liquidity is
    provisioned as an abundant external pool.
  - Constant drawn rate per run (no live IBasicInterestRateStrategy
    recomputation) -- accrual itself uses the EXACT on-chain
    calculateLinearInterest formula (MathUtils.sol), not an approximation.
  - Single asset, multiple spokes.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field

RAY = 10**27
SECONDS_PER_YEAR = 365 * 86400


def ray_mul_down(a: int, b: int) -> int:
    return (a * b) // RAY


def ray_mul_up(a: int, b: int) -> int:
    prod = a * b
    return prod // RAY + (1 if prod % RAY else 0)


def ray_div_down(a: int, b: int) -> int:
    return (a * RAY) // b


def ray_div_up(a: int, b: int) -> int:
    prod = a * RAY
    return prod // b + (1 if prod % b else 0)


def from_ray_up(a: int) -> int:
    return a // RAY + (1 if a % RAY else 0)


def calculate_linear_interest(rate_ray: int, dt_seconds: int) -> int:
    return RAY + (rate_ray * dt_seconds) // SECONDS_PER_YEAR


class InvariantViolation(AssertionError):
    pass


class Revert(Exception):
    pass


@dataclass
class SpokeState:
    name: str
    drawn_shares: int = 0
    deficit_ray: int = 0
    added_shares: int = 10**24
    halted: bool = False
    active: bool = True


@dataclass
class AssetState:
    drawn_index: int = RAY
    drawn_shares: int = 0
    liquidity: int = 10**33
    deficit_ray: int = 0
    drawn_rate: int = 0
    last_update_timestamp: int = 0
    spokes: dict = field(default_factory=dict)

    def spoke(self, name: str) -> SpokeState:
        if name not in self.spokes:
            self.spokes[name] = SpokeState(name)
        return self.spokes[name]

    def drawn_assets(self) -> int:
        return ray_mul_up(self.drawn_shares, self.drawn_index)


def accrue(asset: AssetState, now: int) -> None:
    if now == asset.last_update_timestamp:
        return
    if asset.drawn_shares == 0:
        asset.last_update_timestamp = now
        return
    dt = now - asset.last_update_timestamp
    factor = calculate_linear_interest(asset.drawn_rate, dt)
    asset.drawn_index = ray_mul_up(asset.drawn_index, factor)
    asset.last_update_timestamp = now


def draw(asset: AssetState, spoke_name: str, amount: int, now: int) -> int:
    accrue(asset, now)
    spoke = asset.spoke(spoke_name)
    if not spoke.active or spoke.halted:
        raise Revert("SpokeNotActive/Halted")
    if amount > asset.liquidity:
        raise Revert("InsufficientLiquidity")
    shares = ray_div_up(amount, asset.drawn_index)
    if shares == 0:
        raise Revert("InvalidShares")
    asset.drawn_shares += shares
    spoke.drawn_shares += shares
    asset.liquidity -= amount
    return shares


def restore(asset: AssetState, spoke_name: str, drawn_amount: int, now: int) -> int:
    accrue(asset, now)
    spoke = asset.spoke(spoke_name)
    if spoke.halted:
        raise Revert("SpokeHalted")
    shares = ray_div_down(drawn_amount, asset.drawn_index)
    if shares > spoke.drawn_shares:
        raise Revert("SurplusRestore")
    asset.drawn_shares -= shares
    spoke.drawn_shares -= shares
    asset.liquidity += drawn_amount
    return shares


def report_deficit(asset: AssetState, spoke_name: str, drawn_amount: int, now: int):
    accrue(asset, now)
    spoke = asset.spoke(spoke_name)
    if not spoke.active:
        raise Revert("SpokeNotActive")
    shares = ray_div_down(drawn_amount, asset.drawn_index)
    if shares > spoke.drawn_shares:
        raise Revert("SurplusReportDeficit")
    asset.drawn_shares -= shares
    spoke.drawn_shares -= shares
    deficit_amount_ray = shares * asset.drawn_index
    asset.deficit_ray += deficit_amount_ray
    spoke.deficit_ray += deficit_amount_ray
    return shares, deficit_amount_ray


def eliminate_deficit(asset: AssetState, caller_name: str, covered_name: str, amount: int, now: int):
    accrue(asset, now)
    caller = asset.spoke(caller_name)
    covered = asset.spoke(covered_name)
    if not caller.active:
        raise Revert("CallerNotActive")
    deficit_ray = covered.deficit_ray
    if deficit_ray == 0:
        raise Revert("NoDeficit")
    deficit_amount_ray = amount * RAY if amount < from_ray_up(deficit_ray) else deficit_ray
    deficit_to_eliminate = from_ray_up(deficit_amount_ray)
    shares_burned = deficit_to_eliminate
    if shares_burned > caller.added_shares:
        raise Revert("InsufficientAddedShares")
    caller.added_shares -= shares_burned
    asset.deficit_ray -= deficit_amount_ray
    covered.deficit_ray -= deficit_amount_ray
    return shares_burned, deficit_to_eliminate


def check_invariants(asset: AssetState, prev_index: int, step: int, op: str) -> None:
    sum_shares = sum(s.drawn_shares for s in asset.spokes.values())
    if sum_shares != asset.drawn_shares:
        raise InvariantViolation(
            f"[step {step} after {op}] INV-1 broken: sum={sum_shares} != asset={asset.drawn_shares}"
        )
    sum_deficit = sum(s.deficit_ray for s in asset.spokes.values())
    if sum_deficit != asset.deficit_ray:
        raise InvariantViolation(
            f"[step {step} after {op}] INV-2 broken: sum={sum_deficit} != asset={asset.deficit_ray}"
        )
    for name, s in asset.spokes.items():
        if s.drawn_shares < 0 or s.deficit_ray < 0 or s.added_shares < 0:
            raise InvariantViolation(f"[step {step} after {op}] INV-3 broken for spoke {name}")
    if asset.drawn_shares < 0 or asset.deficit_ray < 0 or asset.liquidity < 0:
        raise InvariantViolation(f"[step {step} after {op}] INV-3 broken at asset level")
    if asset.drawn_index < prev_index:
        raise InvariantViolation(
            f"[step {step} after {op}] INV-4 broken: index decreased {prev_index} -> {asset.drawn_index}"
        )


def run_harness(seed: int, n_spokes: int, n_ops: int, rate_bps_per_year: int, dust_heavy: bool = False) -> dict:
    rng = random.Random(seed)
    asset = AssetState(drawn_rate=(RAY * rate_bps_per_year) // 10000)
    spoke_names = [f"spoke_{i}" for i in range(n_spokes)]
    now = 0

    counters = {"draw": 0, "restore": 0, "reportDeficit": 0, "eliminateDeficit": 0,
                "accrue_only": 0, "reverts": 0}
    r01_events = 0
    r02_checks = 0

    for step in range(n_ops):
        prev_index = asset.drawn_index
        s = rng.choice(spoke_names)
        spoke = asset.spoke(s)

        if rng.random() < 0.02:
            spoke.halted = not spoke.halted

        dt = 0 if rng.random() < 0.3 else rng.randint(1, 86400)
        now += dt

        roll = rng.random()
        amount_hi = 3 if dust_heavy else 10**21

        try:
            if roll < 0.45 or spoke.drawn_shares == 0:
                amount = rng.randint(1, amount_hi)
                draw(asset, s, amount, now)
                counters["draw"] += 1
                check_invariants(asset, prev_index, step, "draw")

                if rng.random() < 0.3 and spoke.drawn_shares > 0:
                    pre = spoke.drawn_shares
                    capped = min(amount, asset.drawn_assets())
                    prev_index2 = asset.drawn_index
                    restore(asset, s, capped, now)
                    counters["restore"] += 1
                    check_invariants(asset, prev_index2, step, "restore(R-01 probe)")
                    if 0 < spoke.drawn_shares < pre:
                        r01_events += 1

            elif roll < 0.75:
                max_restorable = ray_mul_down(spoke.drawn_shares, asset.drawn_index)
                if max_restorable == 0:
                    counters["accrue_only"] += 1
                    continue
                amount = rng.randint(1, max_restorable)
                liq_before = asset.liquidity
                restore(asset, s, amount, now)
                counters["restore"] += 1
                check_invariants(asset, prev_index, step, "restore")
                assert asset.liquidity == liq_before + amount
                r02_checks += 1

            elif roll < 0.93:
                max_defaultable = ray_mul_down(spoke.drawn_shares, asset.drawn_index)
                if max_defaultable == 0:
                    counters["accrue_only"] += 1
                    continue
                amount = rng.randint(1, max_defaultable)
                liq_before = asset.liquidity
                report_deficit(asset, s, amount, now)
                counters["reportDeficit"] += 1
                check_invariants(asset, prev_index, step, "reportDeficit")
                assert asset.liquidity == liq_before
                r02_checks += 1

            else:
                candidates = [n for n in spoke_names if asset.spoke(n).deficit_ray > 0]
                covered = rng.choice(candidates) if candidates else s
                if asset.spoke(covered).deficit_ray == 0:
                    counters["accrue_only"] += 1
                    continue
                amount = rng.randint(1, from_ray_up(asset.spoke(covered).deficit_ray))
                eliminate_deficit(asset, s, covered, amount, now)
                counters["eliminateDeficit"] += 1
                check_invariants(asset, prev_index, step, "eliminateDeficit")

        except Revert:
            counters["reverts"] += 1

    return {
        "seed": seed, "n_spokes": n_spokes, "n_ops": n_ops,
        "rate_bps_per_year": rate_bps_per_year,
        "counters": counters,
        "r01_events": r01_events,
        "r02_checks": r02_checks,
        "final_asset_drawn_shares": asset.drawn_shares,
        "final_sum_spoke_drawn_shares": sum(x.drawn_shares for x in asset.spokes.values()),
        "final_asset_deficit_ray": asset.deficit_ray,
        "final_sum_spoke_deficit_ray": sum(x.deficit_ray for x in asset.spokes.values()),
    }


def boundary_matrix() -> list:
    results = []

    a = AssetState()
    draw(a, "s0", 1, now=0)
    restore(a, "s0", 1, now=0)
    results.append(("B-1", "draw(1)/restore(1) at index==RAY", f"residual={a.spoke('s0').drawn_shares}",
                     "PASS (no residual)" if a.spoke("s0").drawn_shares == 0 else "residual observed"))

    # Isolate PURE rounding residual (R-01): move the index away from RAY via
    # unrelated prior activity, THEN draw(x)/restore(x) at that *fixed*
    # (already-moved) index in the same block -- no interest accrues between
    # the draw and the restore, so any residual is rounding-only, not unpaid
    # interest. (An earlier draft of this boundary case accrued interest
    # *between* draw and restore, which conflates unpaid interest with
    # rounding dust -- corrected here.)
    a = AssetState(drawn_rate=RAY // 10)
    draw(a, "s0", 10**12, now=0)          # unrelated prior activity moves the index later
    accrue(a, now=86400 * 30)             # index now off RAY, e.g. ~1.0082 * RAY
    baseline = a.spoke("s0").drawn_shares
    draw(a, "s0", 10**6, now=86400 * 30)  # same 'now' -> restore below sees the SAME index
    restore(a, "s0", 10**6, now=86400 * 30)
    residual = a.spoke("s0").drawn_shares - baseline
    results.append(("B-2", "draw(1e6)/restore(1e6) at a fixed, already-moved index (no interest between the two calls)",
                     f"residual_shares={residual}",
                     "R-01 reproduced (bounded 0/1-share dust)" if residual in (0, 1) else f"UNEXPECTED residual={residual}"))

    a = AssetState()
    draw(a, "s0", 10**6, now=0)
    liq_before = a.liquidity
    report_deficit(a, "s0", 10**6, now=0)
    results.append(("B-3", "reportDeficit(1e6) right after draw(1e6)",
                     f"liquidity_delta={a.liquidity - liq_before}, deficitRay={a.deficit_ray}",
                     "R-02 confirmed (liquidity untouched)" if a.liquidity == liq_before else "liquidity changed"))

    a = AssetState(drawn_rate=RAY)
    draw(a, "s0", 10**9, now=0)
    accrue(a, now=SECONDS_PER_YEAR)
    shares = ray_div_down(1, a.drawn_index)
    results.append(("B-4", "restore(1 wei) at ~2x index", f"shares_from_1_wei={shares}",
                     "0 shares (dust, floor rounding)" if shares == 0 else f"{shares} shares"))

    a = AssetState()
    draw(a, "s0", 10**7, now=0)
    draw(a, "s1", 10**7, now=0)
    report_deficit(a, "s0", 5 * 10**6, now=0)
    report_deficit(a, "s1", 3 * 10**6, now=0)
    eliminate_deficit(a, "s1", "s0", 2 * 10**6, now=0)
    eliminate_deficit(a, "s1", "s0", 10**9, now=0)
    inv2_ok = a.deficit_ray == sum(x.deficit_ray for x in a.spokes.values())
    results.append(("B-5", "multi-spoke eliminateDeficit: partial then capped-full",
                     f"s0.deficitRay={a.spoke('s0').deficit_ray}, asset.deficitRay={a.deficit_ray}",
                     "INV-2 held, s0 deficit zeroed" if inv2_ok and a.spoke("s0").deficit_ray == 0 else "MISMATCH"))

    return results


def main() -> None:
    print("=" * 88)
    print("UltraCore RFT / RFT-SIRM -- Aave V4 Hub drawn/deficit ledger model harness")
    print("=" * 88)

    seeded_configs = [
        (1337, 4, 5000, 500, False),
        (2024, 8, 8000, 200, False),
        (9001, 2, 3000, 10000, False),
        (4242, 3, 8000, 100, False),
    ]

    all_ok = True
    total_ops = 0
    total_r01 = 0
    total_r02 = 0
    total_reverts = 0
    grand_counters = {"draw": 0, "restore": 0, "reportDeficit": 0, "eliminateDeficit": 0}

    print("\n--- Seeded runs ---")
    for seed, n_spokes, n_ops, rate_bps, dust in seeded_configs:
        try:
            r = run_harness(seed, n_spokes, n_ops, rate_bps, dust)
            status = "PASS"
        except InvariantViolation as e:
            all_ok = False
            status = f"FAIL: {e}"
            r = None
        print(f"\nseed={seed} spokes={n_spokes} ops={n_ops} rate={rate_bps/100:.2f}%/yr -> {status}")
        if r:
            c = r["counters"]
            print(f"  ops: {c}")
            print(f"  R-01 dust events: {r['r01_events']}   R-02 checks: {r['r02_checks']}")
            print(f"  INV-1 asset.drawnShares == Sigma(spoke): {r['final_asset_drawn_shares']} == "
                  f"{r['final_sum_spoke_drawn_shares']} -> "
                  f"{r['final_asset_drawn_shares'] == r['final_sum_spoke_drawn_shares']}")
            print(f"  INV-2 asset.deficitRay == Sigma(spoke): {r['final_asset_deficit_ray']} == "
                  f"{r['final_sum_spoke_deficit_ray']} -> "
                  f"{r['final_asset_deficit_ray'] == r['final_sum_spoke_deficit_ray']}")
            total_ops += n_ops
            total_r01 += r["r01_events"]
            total_r02 += r["r02_checks"]
            total_reverts += c["reverts"]
            for k in grand_counters:
                grand_counters[k] += c[k]

    print("\n--- Boundary-sweep runs (dust-heavy, 1-3 wei amounts) ---")
    sweep_seeds = 200
    sweep_ops = 800
    sweep_r01 = 0
    sweep_r02 = 0
    sweep_reverts = 0
    sweep_fail = False
    for sw_seed in range(sweep_seeds):
        try:
            r = run_harness(sw_seed, n_spokes=3, n_ops=sweep_ops, rate_bps_per_year=1000, dust_heavy=True)
        except InvariantViolation as e:
            sweep_fail = True
            all_ok = False
            print(f"  SWEEP FAIL at seed={sw_seed}: {e}")
            break
        sweep_r01 += r["r01_events"]
        sweep_r02 += r["r02_checks"]
        sweep_reverts += r["counters"]["reverts"]
    sweep_total_ops = sweep_seeds * sweep_ops
    print(f"  {sweep_seeds} seeds x {sweep_ops} ops = {sweep_total_ops} ops -> "
          f"{'PASS' if not sweep_fail else 'FAIL'}")
    print(f"  R-01 dust events: {sweep_r01}   R-02 checks: {sweep_r02}   reverts: {sweep_reverts}")

    total_ops += sweep_total_ops
    total_r01 += sweep_r01
    total_r02 += sweep_r02
    total_reverts += sweep_reverts

    print("\n--- Boundary matrix (B-1..B-5) ---")
    for case_id, scenario, observed, label in boundary_matrix():
        print(f"  {case_id}: {scenario}\n        observed: {observed}\n        label: {label}")

    print("\n" + "=" * 88)
    print(f"TOTAL operations executed (seeded + sweep): {total_ops}")
    print(f"  draw={grand_counters['draw']} restore={grand_counters['restore']} "
          f"reportDeficit={grand_counters['reportDeficit']} eliminateDeficit={grand_counters['eliminateDeficit']}")
    print(f"TOTAL R-01 dust events: {total_r01}")
    print(f"TOTAL R-02 liquidity-shape checks passed: {total_r02}")
    print(f"TOTAL expected-path reverts (not failures): {total_reverts}")
    print(f"OVERALL RESULT: {'ALL INVARIANTS HELD (0 violations)' if all_ok else 'VIOLATIONS DETECTED -- see above'}")
    print("=" * 88)
    print("\nLabel: model-level, deterministic, boundary-seeded. Not bytecode-level.")
    print("No invariant violation -> no novel Class A/B finding from this PoC alone.")
    print("R-01/R-02 are design notes, explicitly not claimed as vulnerabilities.")


if __name__ == "__main__":
    main()
