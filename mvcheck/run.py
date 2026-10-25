"""python -m mvcheck.run <first_seed> <n_seeds> <suite> [out.json]   suite: dev | held

Each scenario is run for every seed. `claim` = the method says the fix saved >= 3% (and for mvcheck, that it can prove it).
False claim = claim when the true savings are 0. Detection = claim when true savings >= 5%.
"""
import json, sys
import numpy as np
from .sim import build
from .methods import METHODS

SUITES = dict(
    dev=[
        ("null, same weather", dict(s=0.0)),
        ("null, post 5 C warmer", dict(s=0.0, shift=5.0)),
        ("null, post 5 C colder", dict(s=0.0, shift=-5.0)),
        ("null, school break in post window", dict(s=0.0, break_in_post=True)),
        ("real 6%", dict(s=0.06)),
        ("real 12%", dict(s=0.12)),
        ("real 6%, post 5 C colder", dict(s=0.06, shift=-5.0)),
    ],
    held=[
        ("null, hot climate, post 6 C warmer", dict(s=0.0, shift=6.0, climate="hot")),
        ("null, cold climate, post 6 C colder", dict(s=0.0, shift=-6.0, climate="cold")),
        ("null, 6-month baseline, break in post", dict(s=0.0, n_pre=183, break_in_post=True)),
        ("null, unflagged closure in post", dict(s=0.0, hidden_closure=True)),
        ("null, noisy meter (10%) + break", dict(s=0.0, noise=0.10, ar=0.8, break_in_post=True)),
        ("real 8%, hot climate", dict(s=0.08, climate="hot")),
        ("real 8%, 6-month baseline", dict(s=0.08, n_pre=183)),
        ("real 8%, noisy meter", dict(s=0.08, noise=0.10, ar=0.8)),
    ],
)


def run(first, n, suite):
    out = {}
    for name, kw in SUITES[suite]:
        row = {m: dict(claims=0, insufficient=0, err=[]) for m in METHODS}
        for seed in range(first, first + n):
            d = build(seed, **kw)
            for m, f in METHODS.items():
                r = f(d)
                row[m]["claims"] += bool(r["claim"])
                row[m]["insufficient"] += r.get("verdict") == "INSUFFICIENT"
                row[m]["err"].append(r["frac"] - kw["s"])
        out[name] = dict(s=kw["s"], n=n, **{m: dict(claims=v["claims"], insufficient=v["insufficient"], bias=float(np.mean(v["err"]))) for m, v in row.items()})
    return out


if __name__ == "__main__":
    first, n, suite = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    R = run(first, n, suite)
    print(f"suite {suite}, seeds {first}..{first + n - 1}: 'claims' = says the fix saved >= 3% (n={n} each); bias = mean(estimated - true savings), in points")
    print(f"  {'scenario':42s} {'true':>5s} | naive claims/bias | reg claims/bias | mvcheck claims (insufficient) /bias")
    for name, r in R.items():
        print(f"  {name:42s} {100 * r['s']:4.0f}% | {r['naive']['claims']:4d} {100 * r['naive']['bias']:+6.1f} | {r['reg']['claims']:4d} {100 * r['reg']['bias']:+6.1f} | "
              f"{r['mvcheck']['claims']:4d} ({r['mvcheck']['insufficient']:3d}) {100 * r['mvcheck']['bias']:+6.1f}")
    if len(sys.argv) > 4:
        json.dump(R, open(sys.argv[4], "w"), indent=1)
