from AlgorithmImports import *
from typing import List, Dict

class DataLoader:
    def __init__(self, algorithm: QCAlgorithm, symbols: List[str], resolution: Resolution):
        self.algorithm = algorithm
        self.symbols = [algorithm.AddEquity(s, resolution).Symbol for s in symbols]
        self.resolution = resolution
        self.data = {s: None for s in self.symbols}

    def update(self, data: Slice) -> Dict[Symbol, TradeBar]:
        for symbol in self.symbols:
            if symbol in data and data[symbol] is not None:
                self.data[symbol] = data[symbol]
        return self.data

    def get_history(self, symbol: Symbol, periods: int) -> pd.DataFrame:
        history = self.algorithm.History(symbol, periods, self.resolution)
        return history

    def get_current_data(self, symbol: Symbol) -> TradeBar:
        return self.data.get(symbol)

    def get_all_current_data(self) -> Dict[Symbol, TradeBar]:
        return self.data