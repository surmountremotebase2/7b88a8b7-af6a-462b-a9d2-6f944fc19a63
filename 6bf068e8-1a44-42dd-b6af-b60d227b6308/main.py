from surmount.base_class import Strategy, TargetAllocation
from surmount.logging import log


class TradingStrategy(Strategy):
    @property
    def assets(self):
        return ["SPY", "QQQ"]

    @property
    def interval(self):
        return "1hour"

    def run(self, data):
        n = len(data["ohlcv"])
        log(f"bar {n}")
        if n % 2 == 0:
            return TargetAllocation({"SPY": 0.5, "QQQ": 0.5})
        return TargetAllocation({"SPY": 0.9})