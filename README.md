# mvcheck: when is a "verified savings" claim actually verified?

Edviro's measurement-and-verification page says fixes are "verified over 30 days against the learned baseline" (a model "weather- and schedule-adjusted") and calls the result "audit-grade" (https://edviroenergy.com/measurement-and-verification/). This prototype is a simulator with a **known counterfactual** that asks: over a 30-day post window, how often does each way of computing savings claim a saving that is not there, and when should it refuse to claim?

Simulator: daily kWh = base x day type (weekday / weekend / school break) + heating and cooling terms in temperature + autocorrelated noise. A fix lowers load by a known fraction `s`. The true counterfactual is stored, so true savings are exact.

Methods (claim = "saved >= 3%"):
- `naive`: last 30 days before vs the 30 days after (what a month-over-month bill comparison does).
- `reg`: weather + calendar regression fit on the baseline period, predict the post window.
- `mvcheck`: `reg` plus ASHRAE-Guideline-14-style checks: CV(RMSE) <= 30% and |NMBE| <= 10% on the fit, post weather inside the baseline's range, a savings interval of the Annex B form 1.26 t CV(RMSE) sqrt((1+2/n')/m') with autocorrelation-corrected counts for both the baseline (n') and the post window (m'), and savings visible in both halves of the window. Output: `VERIFIED`, `NOT_VERIFIED` or `INSUFFICIENT` (cannot say).

## Results (100 seeds per row; numbers are claims out of 100)
Dev (the interval was changed once here, before anything was frozen: the first version treated the 30 post days as independent):

| scenario | true | naive | reg | mvcheck (insufficient) |
|---|---|---|---|---|
| no change, same weather | 0% | 76 | 5 | 1 (1) |
| no change, post 5 C warmer | 0% | 100 | 4 | 2 (0) |
| no change, school break in post | 0% | 95 | 11 | 5 (1) |
| real 6% | 6% | 95 | 96 | 92 (1) |
| real 12% | 12% | 100 | 100 | 99 (1) |

Held-out (scenarios and seeds 1000-1099 committed before the first run; no fixes made afterwards):

| scenario | true | naive | reg | mvcheck (insufficient) |
|---|---|---|---|---|
| no change, hot climate, post 6 C warmer | 0% | 0 | 3 | 1 (0) |
| no change, cold climate, post 6 C colder | 0% | 1 | 2 | 0 (49) |
| no change, 6-month baseline, break in post | 0% | 98 | 7 | 5 (2) |
| **no change, unflagged closure in post** | 0% | 99 | **100** | **98** (2) |
| no change, noisy meter (10%, AR 0.8) + break | 0% | 88 | 35 | 8 (2) |
| real 8%, hot climate | 8% | 61 | 100 | 97 (3) |
| real 8%, 6-month baseline | 8% | 99 | 100 | 98 (2) |
| real 8%, noisy meter | 8% | 90 | 70 | 11 (2) |

Read:
- A before/after comparison is badly fooled by weather and calendar. A weather+calendar baseline fixes most of that.
- The interval and fit checks cut false claims further (noisy meter: 35 -> 8 out of 100) and refuse when the weather leaves the baseline's range, at some cost in power: with a 10%-noise meter it can verify only 11 of 100 real 8% savings in 30 days, which is the honest answer at that noise level.
- **It does not catch an unlogged non-routine event.** A 12% closure for 20 days that is not in the calendar looks exactly like savings, and 98/100 nulls are "verified". Only an event log, a longer window or a control site can address that.

## Limits
- Simulated daily data with a model class that matches the baseline fit; real buildings add interval data, controls changes and metering faults.
- The 3% claim threshold, the 30-day window and the 90% interval are my choices; ASHRAE 14's limits are for hourly/monthly data and are applied here to daily data.
- I did not test anything on Edviro data or systems.

## Run
```
python -m unittest tests.test_mvcheck
python -m mvcheck.run 0 100 dev
python -m mvcheck.run 1000 100 held
```
numpy only.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Edviro.
