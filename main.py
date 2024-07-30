from AlgorithmImports import *
from data.data_loader import DataLoader
from features.engineer import FeatureEngineer
from ml_model.lorentzian_knn import LorentzianKNN, MLModelWrapper
from kernels.regression import NadarayaWatsonRationalQuadratic, KernelRegressionIndicator
from signals.generator import SignalGenerator
from trade_management.executor import TradeManager
from risk_management.lorentzian_risk_manager import LorentzianAdaptiveRiskManager
from utils.helpers import initialize_logging
import sys
import os

# Add project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

class LorentzianClassificationAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2010, 1, 1)
        self.SetEndDate(2023, 1, 1)
        self.SetCash(1000000)
        
        # Initialize logging
        self.Logger = initialize_logging(self)

        # Universe Selection
        self.symbols = ["SPY", "AAPL", "GOOGL", "MSFT", "AMZN"]
        self.UniverseSettings.Resolution = Resolution.Minute
        self.SetUniverseSelection(ManualUniverseSelectionModel(self.symbols))

        # Data Management
        self.data_loader = DataLoader(self, self.symbols, self.UniverseSettings.Resolution)

        # Feature Engineering
        self.feature_engineer = FeatureEngineer(self)

        # ML Model
        self.ml_model = MLModelWrapper(
            LorentzianKNN(n_neighbors=5, weights='distance', lorentzian_distance=True),
            self.feature_engineer
        )

        # Kernel Regression
        self.kernel_regression = {}
        for symbol in self.symbols:
            symbol_obj = self.AddEquity(symbol, self.UniverseSettings.Resolution).Symbol
            kr_indicator = self.RegisterIndicator(
                symbol_obj,
                KernelRegressionIndicator(
                    NadarayaWatsonRationalQuadratic(lookback_window=20, relative_weighting=0.5),
                    self.UniverseSettings.Resolution
                ),
                self.UniverseSettings.Resolution
            )
            self.kernel_regression[symbol_obj] = kr_indicator

        # Signal Generation
        self.signal_generator = SignalGenerator(self.ml_model, self.kernel_regression)

        # Trade Execution
        self.trade_manager = TradeManager(self)

        # Risk Management
        self.SetRiskManagement(LorentzianAdaptiveRiskManager(self))

        # Execution
        self.SetExecution(ImmediateExecutionModel())

        # Portfolio Construction
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())

        # Warm-up period
        self.SetWarmUp(TimeSpan.FromDays(100))

    def OnData(self, data: Slice):
        if self.IsWarmingUp:
            return

        # Update data and features
        try:
            self.data_loader.update(data)
            features = self.feature_engineer.create_features(self.data_loader.current_data)

            # Update ML model
            self.ml_model.update(features)

            # Generate signals
            signals = self.signal_generator.generate_signals(self.data_loader.current_data)

            # Execute trades based on signals
            for symbol, signal in signals.items():
                if signal != 0:  # 0 represents no action
                    self.trade_manager.execute_trade(symbol, signal)

            # Log current state
            self.log_current_state(signals)
        except Exception as e:
            self.Logger.Error(f"Error in OnData: {str(e)}")

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Logger.Info(f"Order filled: {orderEvent}")

    def OnSecuritiesChanged(self, changes):
        for removed in changes.RemovedSecurities:
            symbol = removed.Symbol
            if symbol in self.kernel_regression:
                self.kernel_regression.pop(symbol)

        for added in changes.AddedSecurities:
            symbol = added.Symbol
            if symbol not in self.kernel_regression:
                kr_indicator = self.RegisterIndicator(
                    symbol,
                    KernelRegressionIndicator(
                        NadarayaWatsonRationalQuadratic(lookback_window=20, relative_weighting=0.5),
                        self.UniverseSettings.Resolution
                    ),
                    self.UniverseSettings.Resolution
                )
                self.kernel_regression[symbol] = kr_indicator

    def log_current_state(self, signals):
        self.Logger.Info("--- Current State ---")
        self.Logger.Info(f"Portfolio value: ${self.Portfolio.TotalPortfolioValue}")
        self.Logger.Info(f"Cash: ${self.Portfolio.Cash}")
        for symbol in self.symbols:
            holding = self.Portfolio[symbol]
            signal = signals.get(symbol, 0)
            self.Logger.Info(f"{symbol}: Quantity={holding.Quantity}, Signal={signal}")
        self.Logger.Info("--------------------")

if __name__ == "__main__":
    from datetime import datetime

    start_date = datetime(2010, 1, 1)
    end_date = datetime(2023, 1, 1)
    
    qc = QuantConnect.Python.PythonQuandl()
    qc.Initialize()
    qc.SetStartDate(start_date)
    qc.SetEndDate(end_date)
    qc.SetCash(1000000)
    qc.AddAlgorithm(LorentzianClassificationAlgorithm)
    results = qc.Run()
    
    print(results)
