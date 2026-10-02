"""
TRIPLE BULLET -- 5 tickers, 3 slots, per-ticker exits.

Updated 2026-09-08. ONE change from the version that ran 09-02 to 09-08:
an unguarded KeyError in the entry path is now guarded. Nothing else
moved. Surmount 12-month backtest of this exact file:

    total return 374.71%   maxDD 37.92%   Sharpe 2.59   Calmar 9.93
    2.75 trades/day        (unchanged file: 372.23% / 37.69% / 2.59)

    SOXL   35% take profit,  8% trailing stop
    AGQ    30%              12%
    GDXU   25%              12%
    TECL   10%               4%
    UCO     3%               8%

    entry   price > its own 12-bar VWAP
            AND price > its own 200-bar mean
            AND bar volume >= 1.8x its own 20-bar average
            highest relative volume wins ties
            one new position per bar, THREE positions max, 33.33% each

--------------------------------------------------------------------------
THE CHANGE -- AN UNGUARDED KeyError IN THE ENTRY PATH

`hist` is built as [b[t] for b in d if t in b], skipping bars the ticker
is missing from, so a ticker can score off its LAST AVAILABLE bar while
being absent from the CURRENT one. The old code then did:

    "entry_price": d[-1][best]["close"]      # KeyError

Reproduced against the previous file: KeyError on the winning ticker,
unhandled. A ticker is omitted from a bar when it had no trades in that
5-minute window, which the thin names (AGQ, UCO, GDXU) do far more often
than SOXL or TECL. The exit loop has always guarded for this; the entry
path did not. The fix walks candidates by descending RVOL and takes the
best one actually PRESENT, so a missing ticker costs the next-best name
rather than the whole bar.

Surmount confirm a throw is survivable ("Repeated when the cycle
throws"), so this costs a bar, not the engine. Guarded anyway.

THE LOCAL HARNESS CANNOT CATCH THIS -- it passes every ticker in every
bar, so the branch never runs there. That is also why it is inert in a
backtest, and both A/Bs confirmed it to the dollar.

--------------------------------------------------------------------------
BEFORE CHANGING ANYTHING ELSE -- WHAT SURMOUNT ACTUALLY DOES
(their engineering team, 2026-09-08. Everything in this project dated
before then about platform behaviour was inferred from watching trades.)

`data["holdings"]` IS NOT POSITIONS. It is "the strategy's own last
non-None return value, zero-filled for every asset in assets... target
weights, not positions. Nothing from the broker feeds back."

So `_observed_weight()` below reads back the number THIS FILE last
submitted, not the weight a position drifted to. Live it returns 0.3333
because that is what was sent, so the drifted-weight logic is a NO-OP
and every submission resets all three positions to a flat 33.33%. That
is the trimming seen on 09-01 -- a 4.01% UCO gain producing a 2.60%
sell -- and the mechanism is now confirmed.

IT ONLY LOOKS FIXED IN BACKTEST. The local harness computes holdings
from real share counts, so the strategy submits genuine drifted weights
and the rebalance is harmless there. Surmount confirm this exact
live/backtest gap and are fixing it.

AND THE TRIMMING IS WORTH +69 CAGR POINTS. DO NOT "FIX" IT.
`backtest_surmount.py --holdings-mode echo` reproduces live behaviour.
12 months to 2026-09-01, $5,600, 1 bp:

    holdings mode        final $     CAGR    maxDD  Sharpe  orders/yr
    real (assumed)       $16,698    199.3%   -44.0%   1.95     487
    echo (actual)        $20,545    268.5%   -43.6%   2.18     702

The book cycles positions every few days, so resetting winners down and
losers up is a volatility harvest. Deriving true weights from prices
would REMOVE this. Every backtest in this project therefore UNDERSTATES
the live engine, including the 374.71% above.

AMNESIA RECOVERY IS NOW PERMANENTLY IMPOSSIBLE. `holdings` is this
engine's own memory handed back, so it can never reveal a position the
engine forgot. Worse, that snapshot survives restarts in a database
while `active_positions` does not -- after a restart it would fire on
every ticker and re-adopt at the wrong basis.

--------------------------------------------------------------------------
TESTED AND REJECTED -- DO NOT REDO THESE

POSITION SIZE 31% instead of 33.33%. The local harness liked it at every
value, monotone in drawdown and Sharpe. Surmount disagreed: 372.23% ->
349.69%, -22.5 POINTS, for 1.8 points of drawdown, on IDENTICAL 237
entries. The harness clips buys to available cash
(`spend = min(delta, cash)`) so at 99.99% invested it starves itself;
Surmount does not. Harness artifact. Reverted.

EXPLICIT ZEROS in the allocation dict -- Surmount's own recommendation,
to avoid a live/backtest discrepancy on the empty-dict path. Measured on
their backtester: 374.71% -> 286.35%, drawdown 37.92% -> 42.94%.
-88 POINTS. Naming a ticker at 0.0 is NOT equivalent to omitting it.
Reverted. Do not re-apply without re-testing.

--------------------------------------------------------------------------
KNOWN, UNMEASURED -- 39 SAME-BAR EXIT -> RE-ENTRY EVENTS

The entry loop skips tickers in `active_positions` but NOT tickers in
`exited_tickers`. A take-profit can fire and the same ticker be rebought
two lines later IN THE SAME BAR, at the same price, with a fresh entry
price and a fresh peak. 39 times in the 12-month log = 16% of all
entries, mostly UCO and GDXU.

Structurally the same mechanism as the amnesia-recovery block removed
after it measured 372% -> 283%. NOT new and NOT a regression -- it is
inside every backtest this engine has ever produced. Nobody has measured
it. Left alone deliberately pending a controlled A/B.

--------------------------------------------------------------------------
HOW THE EXITS WERE FOUND

Each ticker was tested ALONE -- one ticker, one slot, full size -- so the
only thing varying is its own exit pair against its own price action.
Earlier attempts changed one ticker's stop while the others competed for
slots and then measured the PORTFOLIO, which measured the reshuffle.

Selection was by COMPOUNDED growth across three INDEPENDENT years
(Y1 23/24 x Y2 24/25 x Y3 25/26). NOT ONE TICKER WANTED the flat 25%/12%
default, which had never itself been tested -- it ranked 12th of 30 for
SOXL and 19th of 30 for TECL.

The exits PASSED walk-forward: fitted on Y1+Y2 and traded blind through
Y3 they returned 267.8% against the in-sample 202.5% and a flat
default's 51.6%. THE ROSTER DID NOT GET THAT TEST AND CANNOT -- GDXU is
in the book because it did well 2023-26.

GDXU runs 25%/12%, changed 2026-09-01. Every 12% variant beat the old
20/20 on compounded growth and turned both losing years positive. The
deciding evidence was reaction time: in the June 2026 metals crash 20/20
lost 20% in TWO DAYS, 25/12 in six.

CONCENTRATION, the main risk: TECL and SOXL correlate 0.91 and are close
to one instrument; GDXU and AGQ are both metals.

NO REGIME AWARENESS. The longest lookback is 200 five-minute bars, about
2.6 trading days. The off-switch is manual and deliberate.

--------------------------------------------------------------------------
PERSISTENT MEMORY -- ADDED 2026-09-29, THE ONLY CHANGE FROM THE 09-16 FILE

`persistent_attrs = ["active_positions"]` below. Surmount saves and
restores exactly the names listed, so `active_positions` -- entry price
and tracked peak for every open position -- now survives a restart.

WHY IT MATTERS. Before this, a Surmount deployment rebuilt the strategy
from __init__ and every open position lost its stop and its target. That
is the 2026-09-15 UCO incident: the position stayed in the account, the
engine forgot it existed, and the next entry signal sold it as a side
effect at an arbitrary price. The standing mitigation was to flatten the
book by hand before every announced deployment. This replaces that.

ONLY `active_positions` IS DECLARED. `exited_tickers` is reset to [] at
the top of every run(), so it is per-bar scratch, not state -- declaring
it would persist nothing meaningful. Surmount's own example lists both;
for this file that would be cargo cult.

NEVER DECLARE `take_profits`, `trailing_stops`, `tickers` OR ANY OTHER
SETTING. Per Surmount's docs, a declared name is read from the saved
snapshot and NOT from the code -- so changing GDXU from 20/20 to 25/12
would silently fail to take effect. That is the 2026-09-11 bug recreated
permanently by our own hand. Settings must stay in __init__, undeclared,
so an edit actually applies.

THE NEW OPERATING RULE, AND IT CUTS BOTH WAYS:

  SURMOUNT's deployments  -> nothing to do. Memory survives. This is the
                             entire point and it retires the flatten rule.
  YOUR OWN pause/restart  -> a pause LIQUIDATES the account but the saved
                             memory SURVIVES, so the engine would restart
                             believing it owns what was just sold: slots
                             look full, entries are silently skipped, and
                             it eventually acts on a stale cost basis.
                             BE FLAT, or bump `memory_version`, which
                             discards the snapshot and starts from
                             __init__.

DEPLOY PROCEDURE UNCHANGED: liquidate, then deploy as a BRAND NEW
strategy. A new strategy has no saved snapshot, so it starts clean.
Harrison confirmed this is the recommended route (2026-09-29).

INERT IN BACKTEST, BY DESIGN. Surmount: "Declared attributes are ordinary
in-process values in a backtest... every backtest starts from the
__init__ values." So this file must reproduce the previous one TO THE
DOLLAR on a Surmount backtest. If it does not, something else changed --
that A/B is the control, and it is the only pre-deploy check available.

TYPES ARE ALREADY SAFE. Surmount accepts dict (string keys), list, str,
int, float, bool, None and nesting of those, and REJECTS sets, tuples,
DataFrames and datetimes outright. `active_positions` is
{str: {str: float}} throughout, so no conversion is needed.
"""

from surmount.base_class import Strategy, TargetAllocation
from surmount.logging import log
import pandas as pd
import numpy as np


class TradingStrategy(Strategy):

    # Surmount saves and restores exactly these names across a restart.
    # ONLY state belongs here -- never settings. See the docstring.
    persistent_attrs = ["active_positions"]

    # Bump this to DISCARD the saved snapshot and start from __init__.
    # Needed after any manual liquidation of a running strategy.
    memory_version = 1

    def __init__(self):
        self.tickers = ["TECL", "SOXL", "AGQ", "UCO", "GDXU"]

        # 33.33%. A smaller size was tested end to end on 2026-09-08 and
        # REJECTED -- it cost 22.5 points of return on Surmount to save
        # 1.8 points of drawdown. See the docstring before changing it.
        self.allocation_size = 0.3333
        self.max_positions = 3
        self.vwap_len = 12            # bars, = 1 hour
        self.rvol_threshold = 1.8

        # --- EXITS, PER TICKER -------------------------------------
        #   ticker   TP / stop   3yr growth   worst yr   worst DD
        #   SOXL      35% /  8%     11.47x      +64.7%     -54.9%
        #   AGQ       30% / 12%      4.22x      +28.1%     -61.3%
        #   GDXU      25% / 12%   (changed 2026-09-01, see docstring)
        #   TECL      10% /  4%      3.87x      +48.4%     -41.0%   (edge)
        #   UCO        3% /  8%      1.83x       +6.5%     -37.5%   (edge)
        #
        # TECL and UCO winners sit on a grid EDGE, so those two are floors
        # rather than peaks and may improve further outside the range.
        self.take_profits = {
            "TECL": 0.10,
            "SOXL": 0.35,
            "AGQ":  0.30,
            "UCO":  0.03,
            "GDXU": 0.25,
        }
        self.trailing_stops = {
            "TECL": 0.04,
            "SOXL": 0.08,
            "AGQ":  0.12,
            "UCO":  0.08,
            "GDXU": 0.12,
        }
        # fallback for any ticker missing from the dicts above
        self.take_profit_pct = 0.25
        self.trailing_stop_pct = 0.12

        # {"TICKER": {"entry_price": X, "peak_price": Y, "weight": W}}
        self.active_positions = {}
        self.exited_tickers = []

    @property
    def interval(self):
        return "5min"

    @property
    def assets(self):
        return self.tickers

    def take_profit_for(self, ticker):
        return self.take_profits.get(ticker, self.take_profit_pct)

    def trailing_stop_for(self, ticker):
        return self.trailing_stops.get(ticker, self.trailing_stop_pct)

    def get_conviction_score(self, history):
        if len(history) < 200:
            return 0
        df = pd.DataFrame(history)

        recent_df = df.tail(self.vwap_len)
        vwap = (recent_df["close"] * recent_df["volume"]).sum() / recent_df["volume"].sum()
        current_price = df["close"].iloc[-1]

        avg_vol = df["volume"].tail(20).mean()
        rvol = df["volume"].iloc[-1] / avg_vol if avg_vol > 0 else 0

        sma_macro = df["close"].tail(200).mean()

        if current_price > vwap and current_price > sma_macro and rvol >= self.rvol_threshold:
            return rvol
        return 0

    def _observed_weight(self, ticker, holdings):
        """The weight the platform reports for this ticker, or None.

        NOTE 2026-09-08: on Surmount LIVE this returns the weight this
        strategy last SUBMITTED, not the weight the position has drifted
        to -- `holdings` is our own last return value echoed back. Kept
        because it is correct in backtest, and because the resulting flat
        reset is worth +69 CAGR points live. See the docstring.
        """
        if not holdings:
            return None
        raw = holdings.get(ticker, None)
        if raw is None:
            return None
        try:
            w = float(raw)
        except (TypeError, ValueError):
            return None
        return w if 0.0 < w <= 1.0 else None

    def run(self, data):
        d = data.get("ohlcv")
        if not d:
            return None

        # --- DATA SCRUBBER -----------------------------------------
        # If the platform ever returns lowercase keys, holdings.get("TECL")
        # returns None and _observed_weight silently fails. One line of
        # insurance against a failure that would otherwise be invisible.
        raw_holdings = data.get("holdings", {}) or {}
        holdings = {str(k).upper(): v for k, v in raw_holdings.items()}
        self.exited_tickers = []
        state_changed = False
        newly_entered = set()

        # --- bookkeeping only: record weights, place no trades ------
        for t in self.active_positions:
            observed = self._observed_weight(t, holdings)
            if observed is not None:
                self.active_positions[t]["weight"] = observed

        # --- 1. manage what is held --------------------------------
        for t, m in list(self.active_positions.items()):
            bar = d[-1].get(t)
            if not bar:
                continue
            cp = bar["close"]

            if cp > m["peak_price"]:
                self.active_positions[t]["peak_price"] = cp

            tp = self.take_profit_for(t)
            if cp >= m["entry_price"] * (1 + tp):
                log(f"TAKE PROFIT ({tp:.0%}): {t} exit at {cp}.")
                self.exited_tickers.append(t)
                del self.active_positions[t]
                state_changed = True
                continue

            st = self.trailing_stop_for(t)
            if cp <= m["peak_price"] * (1 - st):
                log(f"SWING STOP ({st:.0%}): {t} exit at {cp}.")
                self.exited_tickers.append(t)
                del self.active_positions[t]
                state_changed = True
                continue

        # --- 2. pick at most one new position ----------------------
        if len(self.active_positions) < self.max_positions:
            scores = {}
            for t in self.tickers:
                if t in self.active_positions:
                    continue
                hist = [b[t] for b in d if t in b]
                if hist:
                    sc = self.get_conviction_score(hist)
                    if sc > 0:
                        scores[t] = sc

            # THE FIX. `hist` skips bars a ticker is missing from, so a
            # ticker can score off its last available bar while being
            # ABSENT from the current one -- which happens whenever it
            # had no trades in that window. The old code reached straight
            # into d[-1][best] and raised KeyError. Take the best
            # candidate that is actually present instead, so a missing
            # ticker costs the next-best name rather than the whole bar.
            best = None
            for cand in sorted(scores, key=scores.get, reverse=True):
                cbar = d[-1].get(cand)
                if cbar and cbar.get("close"):
                    best = cand
                    break

            if best is not None:
                cp = d[-1][best]["close"]
                self.active_positions[best] = {
                    "entry_price": cp,
                    "peak_price": cp,
                    "weight": self.allocation_size,
                }
                newly_entered.add(best)
                state_changed = True
                log(f"SWING ENTRY ({self.allocation_size:.0%}): {best} | RVOL: {scores[best]:.2f}")

        # --- 3. submit the book ------------------------------------
        # A new position gets allocation_size. Existing ones are submitted
        # at their tracked weight. NOTE: explicit zeros for the untraded
        # tickers were tested here on 2026-09-08 and cost 88 points --
        # omitting them is correct. See the docstring.
        if state_changed:
            alloc = {}
            for t, m in self.active_positions.items():
                alloc[t] = (self.allocation_size if t in newly_entered
                            else m.get("weight", self.allocation_size))
            total = sum(alloc.values())
            if total > 1.0:
                alloc = {t: w / total for t, w in alloc.items()}
            log("ALLOC: " + ", ".join(f"{t} {w:.1%}" for t, w in alloc.items()))
            return TargetAllocation(alloc)

        return None