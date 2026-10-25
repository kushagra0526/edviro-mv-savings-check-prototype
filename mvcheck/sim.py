"""Daily building energy simulator with a known counterfactual.

kWh_d = base * daytype + heat_slope * max(0, 18 - T) + cool_slope * max(0, T - 18) + AR(1) noise (multiplicative, ~4%).
Day types: weekday 1.0, weekend 0.45, school break 0.55 (calendar known to the analyst).
An intervention at day d0 lowers the load by fraction s (true savings). Optional unflagged closure: -12% for 20 days after d0 (not in the calendar).
"""
import numpy as np

CLIMATES = dict(temperate=dict(mean=12, amp=11, heat=9.0, cool=4.0), hot=dict(mean=22, amp=8, heat=3.0, cool=12.0), cold=dict(mean=4, amp=14, heat=12.0, cool=2.0))


def build(seed, climate="temperate", s=0.0, shift=0.0, break_in_post=False, hidden_closure=False, n_pre=365, noise=0.04, ar=0.5, base=1000.0):
    r = np.random.default_rng(seed)
    c = CLIMATES[climate]
    d0 = 400 if n_pre >= 365 else 400
    days = d0 + 30
    doy = np.arange(days)
    seasonal = c["mean"] - c["amp"] * np.cos(2 * np.pi * doy / 365)
    a = np.zeros(days)
    for i in range(1, days):
        a[i] = 0.7 * a[i - 1] + r.normal(0, 2.5)
    T = seasonal + a
    T[d0:] += shift                                             # post period is warmer/colder than the baseline period would suggest
    dow = doy % 7
    kind = np.where(dow >= 5, 1, 0)                              # 1 weekend
    brk = np.zeros(days, bool)
    brk[(doy % 365) >= 355] = True                               # winter break
    brk[(doy % 365) < 5] = True
    if break_in_post:
        brk[d0 + 8:d0 + 22] = True                               # a school break inside the 30-day post window (calendar knows)
    mult = np.where(brk, 0.55, np.where(kind == 1, 0.45, 1.0))
    expected = base * mult + c["heat"] * 10 * np.maximum(0, 18 - T) + c["cool"] * 10 * np.maximum(0, T - 18)
    e = np.zeros(days)
    for i in range(1, days):
        e[i] = ar * e[i - 1] + r.normal(0, noise)
    cf = expected * (1 + e)                                       # what the building would have used with no intervention
    actual = cf.copy()
    actual[d0:] *= (1 - s)
    if hidden_closure:
        actual[d0 + 5:d0 + 25] *= 0.88
    pre = slice(max(0, d0 - n_pre), d0)
    post = slice(d0, d0 + 30)
    return dict(T=T, kwh=actual, cf=cf, kind=kind, brk=brk, d0=d0, pre=pre, post=post, s=s, climate=climate)
