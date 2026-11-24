from surmount.base_class import Strategy, TargetAllocation
from surmount.logging import log


class TradingStrategy(Strategy):
    @property
    def assets(self):
        return ["BTC-USD", "SPY"]

    @property
    def interval(self):
        return "4hour"

    def run(self, data):
        n = len(data["ohlcv"])
        log(f"bar {n}")
        if n % 2 == 0:
            return TargetAllocation({"BTC-USD": 0.3, "SPY": 0.6})
        return TargetAllocation({"SPY": 0.9})