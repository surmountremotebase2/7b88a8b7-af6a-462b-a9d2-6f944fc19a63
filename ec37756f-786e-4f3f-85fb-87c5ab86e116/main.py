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
            {"NVDA": 0.25, "MSFT": 0.25, "AWRE": .5},
            {"NVDA": 0.25, "MSFT": 0.25, "AWRE": .5},
            {"NVDA": 0.25, "MSFT": 0.25, "AWRE": .5},
            {"NVDA": 0.50, "MSFT": 0.49, "AWRE": .01},
            {"NVDA": 0.50, "MSFT": 0.49, "AWRE": .01},
            {"NVDA": 0.50, "MSFT": 0.49, "AWRE": .01},
        ]

    @property
    def assets(self):
        return ["NVDA", "MSFT", "QQQ"]

    @property
    def interval(self):
        # Real accepted values: "1min" | "5min" | "1hour" | "4hour" | "1day"
        return "5min"

    def run(self, data):
        shape = self._shapes[self.count % len(self._shapes)]
        self.count += 1  # runner persists this after run() returns
        return TargetAllocation(shape)