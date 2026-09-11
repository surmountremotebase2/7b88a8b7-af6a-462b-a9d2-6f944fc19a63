from surmount.base_class import Strategy, TargetAllocation


class TradingStrategy(Strategy):
    """Staging test/monitor strategy. Cycles through allocation shapes that
    exercise buy, sell, orphan, partial/residual-cash, full-liquidation, and
    over-allocation normalization. Deterministic and restart-safe via
      self.count, which the live runner persists across invocations."""

    def __init__(self):
        # Overwritten with the persisted value before run() by the runner
        # (base_class: if hasattr(strategy, "count"): strategy.count = tracker.get_count()).
        self.count = 0

        # One entry per rebalance. Ordered so consecutive steps force the
        # transitions we want to test (deploy -> orphan -> rotate -> all-cash -> redeploy ...).
        self._shapes = [
            {"NVDA": 0.33, "MSFT": 0.33, "QQQ": 0.33},  # 0 happy path, ~full deploy
            {"NVDA": 0.5,  "MSFT": 0.25},               # 1 DROP QQQ (orphan) + 25% cash residual
            {"QQQ": 1.0},                               # 2 rotate fully to QQQ (orphans NVDA + MSFT)
            {},                                         # 3 100% cash (full liquidation)
            {"NVDA": 0.33, "MSFT": 0.33, "QQQ": 0.33},  # 4 happy path, ~full deploy      
            {"NVDA": 0.0},                              # 5 all cash with a 0 and orphaned tickers
            {"NVDA": 0.4},                              # 6 40% NVDA 
            {"NVDA": 0.33, "MSFT": 0.33, "QQQ": 0.33},  # 7 back to full (re-buys MSFT + QQQ)
            {"NVDA": 0.6,  "MSFT": 0.6},                # 8 sum=1.2 -> SDK normalizes to ~0.5/0.5
            {"NVDA": 0.33, "MSFT": 0.33, "QQQ": 0},     # 9 QQQ present-at-0: NOT an orphan (contrast w/ step 1)
            {"AWRE": .90, "SPY": .10}                   # 10 AWRE (Non fractionable) and spy
        ]

    @property
    def assets(self):
        return ["NVDA", "MSFT", "QQQ", "AWRE"]

    @property
    def interval(self):
        # Real accepted values: "1min" | "5min" | "1hour" | "4hour" | "1day"
        return "5min"

    def run(self, data):
        shape = self._shapes[self.count % len(self._shapes)]
        self.count += 1  # runner persists this after run() returns
        return TargetAllocation(shape)