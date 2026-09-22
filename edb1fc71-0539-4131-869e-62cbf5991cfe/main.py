from surmount.base_class import Strategy, TargetAllocation
import logging

logger = logging.getLogger("memprobe")


class TradingStrategy(Strategy):
    """Staging probe for declared strategy-state persistence.

    Keeps a run counter and a per-ticker peak close on the instance and
    declares both as durable, so a session restart should restore them
    instead of starting from the values set in __init__.
    """

    persistent_attrs = ["runs", "peaks"]
    memory_version = 1

    def __init__(self):
        self.tickers = ["SPY"]
        self.runs = 0
        self.peaks = {}

    @property
    def interval(self):
        return "5min"

    @property
    def assets(self):
        return self.tickers

    def run(self, data):
        self.runs += 1
        ohlcv = data["ohlcv"]
        if ohlcv:
            for ticker in self.tickers:
                bar = ohlcv[-1].get(ticker)
                if bar:
                    close = float(bar["close"])
                    if self.peaks.get(ticker) is None or close > self.peaks[ticker]:
                        self.peaks[ticker] = close
        logger.info("MEMPROBE runs=%s peaks=%s", self.runs, self.peaks)
        weight = 1.0 / len(self.tickers)
        return TargetAllocation({t: weight for t in self.tickers})