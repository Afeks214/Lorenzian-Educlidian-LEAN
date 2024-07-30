from AlgorithmImports import *
from typing import Dict

class TradeExecutor:
    def __init__(self, algorithm: QCAlgorithm):
        self.algorithm = algorithm

    def execute_trade(self, symbol: Symbol, direction: int, quantity: int):
        if direction == 1:
            self.algorithm.MarketOrder(symbol, quantity)
            self.algorithm.Log(f"Buying {quantity} shares of {symbol}")
        elif direction == -1:
            self.algorithm.MarketOrder(symbol, -quantity)
            self.algorithm.Log(f"Selling {quantity} shares of {symbol}")

class PositionManager:
    def __init__(self, algorithm: QCAlgorithm):
        self.algorithm = algorithm

    def get_position(self, symbol: Symbol) -> float:
        return self.algorithm.Portfolio[symbol].Quantity

    def get_all_positions(self) -> Dict[Symbol, float]:
        return {symbol: self.get_position(symbol) for symbol in self.algorithm.Portfolio.Keys}

class RiskManager:
    def __init__(self, algorithm: QCAlgorithm, max_position_size: float = 0.1):
        self.algorithm = algorithm
        self.max_position_size = max_position_size

    def calculate_position_size(self, symbol: Symbol) -> int:
        price = self.algorithm.Securities[symbol].Price
        portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
        max_quantity = int((portfolio_value * self.max_position_size) / price)
        return max_quantity

    def check_risk_limits(self, symbol: Symbol, quantity: int) -> bool:
        current_position = self.algorithm.Portfolio[symbol].Quantity
        max_allowed = self.calculate_position_size(symbol)
        return abs(current_position + quantity) <= max_allowed

class TradeManager:
    def __init__(self, algorithm: QCAlgorithm):
        self.algorithm = algorithm
        self.executor = TradeExecutor(algorithm)
        self.position_manager = PositionManager(algorithm)
        self.risk_manager = RiskManager(algorithm)

    def place_trade(self, symbol: Symbol, direction: int):
        quantity = self.risk_manager.calculate_position_size(symbol)
        if self.risk_manager.check_risk_limits(symbol, quantity * direction):
            self.executor.execute_trade(symbol, direction, quantity)
        else:
            self.algorithm.Log(f"Trade for {symbol} exceeds risk limits. Not executed.")

    def manage_positions(self, signals: Dict[Symbol, int]):
        for symbol, signal in signals.items():
            current_position = self.position_manager.get_position(symbol)
            if (signal == 1 and current_position <= 0) or (signal == -1 and current_position >= 0):
                self.place_trade(symbol, signal)