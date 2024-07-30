# data/heikin_ashi.py

from AlgorithmImports import *
from typing import Dict

class HeikinAshi:
    def __init__(self, algorithm: QCAlgorithm):
        self.algorithm = algorithm
        self.previous_ha: Dict[str, TradeBar] = {}

    def convert(self, data: Dict[str, TradeBar]) -> Dict[str, TradeBar]:
        ha_data = {}
        for symbol, bar in data.items():
            ha_data[symbol] = self.convert_tradebar(symbol, bar)
        return ha_data

    def convert_tradebar(self, symbol: str, tradebar: TradeBar) -> TradeBar:
        if symbol not in self.previous_ha:
            ha_open = tradebar.Open
        else:
            prev_ha = self.previous_ha[symbol]
            ha_open = (prev_ha.Open + prev_ha.Close) / 2

        ha_close = (tradebar.Open + tradebar.High + tradebar.Low + tradebar.Close) / 4
        ha_high = max(tradebar.High, ha_open, ha_close)
        ha_low = min(tradebar.Low, ha_open, ha_close)

        ha_bar = TradeBar(
            tradebar.Time, 
            tradebar.Symbol, 
            ha_open, 
            ha_high, 
            ha_low, 
            ha_close, 
            tradebar.Volume
        )

        self.previous_ha[symbol] = ha_bar
        return ha_bar

    def initialize_history(self, symbol: str, history: IEnumerable[TradeBar]) -> None:
        ha_open = history[0].Open
        for bar in history:
            ha_close = (bar.Open + bar.High + bar.Low + bar.Close) / 4
            ha_high = max(bar.High, ha_open, ha_close)
            ha_low = min(bar.Low, ha_open, ha_close)

            self.previous_ha[symbol] = TradeBar(
                bar.Time, 
                bar.Symbol, 
                ha_open, 
                ha_high, 
                ha_low, 
                ha_close, 
                bar.Volume
            )

            ha_open = (ha_open + ha_close) / 2