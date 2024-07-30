from AlgorithmImports import *
from enum import Enum
from typing import Dict, List
import numpy as np

class SignalType(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0

class SignalGenerator:
    def __init__(self, algorithm: QCAlgorithm, symbols: List[Symbol], ml_model_wrapper: MLModelWrapper):
        self.algorithm = algorithm
        self.symbols = symbols
        self.ml_model_wrapper = ml_model_wrapper
        self.current_positions: Dict[Symbol, float] = {symbol: 0 for symbol in symbols}
        self.last_signals: Dict[Symbol, SignalType] = {symbol: SignalType.HOLD for symbol in symbols}

    def generate_signals(self) -> Dict[Symbol, SignalType]:
        signals = {}
        for symbol in self.symbols:
            prediction = self.ml_model_wrapper.Current.Value[symbol]['prediction']
            signal = self._get_signal(symbol, prediction)
            signals[symbol] = signal
        return signals

    def _get_signal(self, symbol: Symbol, prediction: float) -> SignalType:
        threshold = self.algorithm.Settings.signal_threshold
        if prediction > threshold and self.current_positions[symbol] <= 0:
            return SignalType.BUY
        elif prediction < -threshold and self.current_positions[symbol] >= 0:
            return SignalType.SELL
        return SignalType.HOLD

    def execute_trades(self, signals: Dict[Symbol, SignalType]):
        for symbol, signal in signals.items():
            if signal != self.last_signals[symbol]:
                self._execute_trade(symbol, signal)
                self.last_signals[symbol] = signal

    def _execute_trade(self, symbol: Symbol, signal: SignalType):
        if signal == SignalType.BUY:
            self.algorithm.SetHoldings(symbol, 1)  # Full long position
            self.current_positions[symbol] = 1
            self.algorithm.Log(f"Buying {symbol}")
        elif signal == SignalType.SELL:
            self.algorithm.SetHoldings(symbol, -1)  # Full short position
            self.current_positions[symbol] = -1
            self.algorithm.Log(f"Selling {symbol}")
        # HOLD signal does nothing

    def update_positions(self):
        for symbol in self.symbols:
            self.current_positions[symbol] = self.algorithm.Portfolio[symbol].Quantity

class SignalManagerAlphaModel(AlphaModel):
    def __init__(self, symbols: List[Symbol], ml_model_wrapper: MLModelWrapper):
        self.symbols = symbols
        self.ml_model_wrapper = ml_model_wrapper
        self.signal_generator = None

    def Initialize(self, algorithm: QCAlgorithm, portfolio: SecurityPortfolioManager):
        self.signal_generator = SignalGenerator(algorithm, self.symbols, self.ml_model_wrapper)

    def Update(self, algorithm: QCAlgorithm, data: Slice) -> List[Insight]:
        if not self.ml_model_wrapper.IsReady:
            return []

        self.signal_generator.update_positions()
        signals = self.signal_generator.generate_signals()
        self.signal_generator.execute_trades(signals)

        insights = []
        for symbol, signal in signals.items():
            if signal != SignalType.HOLD:
                direction = InsightDirection.Up if signal == SignalType.BUY else InsightDirection.Down
                insights.append(Insight.Price(symbol, timedelta(days=1), direction))

        return insights

class LorentzianClassificationAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2010, 1, 1)
        self.SetCash(100000)
        
        self.symbols = [self.AddEquity(ticker, Resolution.Daily).Symbol for ticker in ["SPY", "AAPL", "GOOGL"]]
        
        self.feature_engineer = FeatureEngineer(self)
        for symbol in self.symbols:
            self.feature_engineer.create_features(symbol)
        
        self.ml_model_wrapper = MLModelWrapper(self, self.feature_engineer, self.symbols)
        self.RegisterIndicator(self.symbols[0], self.ml_model_wrapper, Resolution.Daily)
        
        self.SetAlpha(SignalManagerAlphaModel(self.symbols, self.ml_model_wrapper))
        
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetExecution(ImmediateExecutionModel())
        self.SetRiskManagement(NullRiskManagementModel())

    def OnData(self, data: Slice):
        pass  # Main logic is handled in the AlphaModel