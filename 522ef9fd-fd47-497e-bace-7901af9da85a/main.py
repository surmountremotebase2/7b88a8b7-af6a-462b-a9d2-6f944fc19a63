from surmount.base_class import Strategy, TargetAllocation


class TradingStrategy(Strategy):
    @property
    def assets(self):
        return ["SPY"]

    @property
    def interval(self):
        return "1day"

    def run(self, data):
        return TargetAllocation({"SPY": 1.0})