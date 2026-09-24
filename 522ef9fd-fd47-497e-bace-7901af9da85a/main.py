from surmount.base_class import Strategy, TargetAllocation

# PG-2907 staging check 2026-09-23
 PG-2907 deploy-flow check
class TradingStrategy(Strategy):
    @property
    def assets(self):
        return ["SPY"]

    @property
    def interval(self):
        return "1day"

    def run(self, data):
        return TargetAllocation({"SPY": 0.9})