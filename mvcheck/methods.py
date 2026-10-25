"""Three ways to say "this fix saved X%" over a 30-day post window.

naive   last 30 days before vs the 30 days after
reg     weather+calendar regression baseline fit on the baseline period; claim if fractional savings >= 3%
mvcheck reg + fit criteria (CV(RMSE) <= 30%, |NMBE| <= 10%, ASHRAE Guideline 14 hourly limits applied to daily data), weather-range check,
        savings interval (Annex B form: 1.26 t CV(RMSE) sqrt((1+2/n')/m'), n' and m' = count (1-rho)/(1+rho)), persistence (both halves show savings)
        -> VERIFIED / NOT_VERIFIED / INSUFFICIENT
"""
import numpy as np

T90 = 1.66


def design(d, idx):
    T = d["T"][idx]
    return np.column_stack([np.ones(len(T)), d["kind"][idx], d["brk"][idx], np.maximum(0, 18 - T), np.maximum(0, T - 18)])


def naive(d):
    pre, post = d["kwh"][d["d0"] - 30:d["d0"]], d["kwh"][d["post"]]
    f = 1 - post.mean() / pre.mean()
    return dict(frac=f, claim=f >= 0.03)


def fit(d):
    ip = np.arange(d["pre"].start, d["pre"].stop)
    X, y = design(d, ip), d["kwh"][ip]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    return b, res, y


def reg(d):
    b, res, y = fit(d)
    ip = np.arange(d["post"].start, d["post"].stop)
    pred = design(d, ip) @ b
    f = 1 - d["kwh"][ip].sum() / pred.sum()
    return dict(frac=f, claim=f >= 0.03)


def mvcheck(d):
    b, res, y = fit(d)
    n, p = len(y), 5
    rmse = np.sqrt(np.sum(res**2) / (n - p))
    cv, nmbe = rmse / y.mean(), res.sum() / ((n - p) * y.mean())
    ip = np.arange(d["post"].start, d["post"].stop)
    pred = design(d, ip) @ b
    act = d["kwh"][ip]
    f = 1 - act.sum() / pred.sum()
    rho = np.corrcoef(res[1:], res[:-1])[0, 1]
    neff = max(5.0, n * (1 - rho) / (1 + rho))
    meff = max(3.0, len(ip) * (1 - rho) / (1 + rho))               # post-period days are autocorrelated too
    u = 1.26 * T90 * cv * np.sqrt((1 + 2 / neff) / meff)
    reasons = []
    if cv > 0.30 or abs(nmbe) > 0.10:
        reasons.append("FIT")
    Tb = d["T"][d["pre"]]
    Tp = d["T"][ip]
    if (Tp.min() < Tb.min() - 1) or (Tp.max() > Tb.max() + 1) or (np.mean((Tp < Tb.min()) | (Tp > Tb.max())) > 0.1):
        reasons.append("EXTRAPOLATED")
    half = len(ip) // 2
    h1, h2 = 1 - act[:half].sum() / pred[:half].sum(), 1 - act[half:].sum() / pred[half:].sum()
    if reasons:
        return dict(frac=f, u=u, verdict="INSUFFICIENT", reasons=reasons, claim=False)
    ok = f - u > 0 and f >= 0.03 and h1 > 0 and h2 > 0
    return dict(frac=f, u=u, verdict="VERIFIED" if ok else "NOT_VERIFIED", reasons=[], claim=ok)


METHODS = dict(naive=naive, reg=reg, mvcheck=mvcheck)
