from AlgorithmImports import *
import numpy as np
from scipy.stats import norm
from typing import Dict, List

class LorentzianAdaptiveRiskManager(RiskManagementModel):
    def __init__(self, algorithm: QCAlgorithm, 
                 base_max_drawdown: float = 0.1, 
                 base_max_leverage: float = 2.0,
                 volatility_lookback: int = 30, 
                 base_max_volatility: float = 0.05,
                 kernel_confidence_threshold: float = 0.7):
        self.algorithm = algorithm
        self.base_max_drawdown = base_max_drawdown
        self.base_max_leverage = base_max_leverage
        self.volatility_lookback = volatility_lookback
        self.base_max_volatility = base_max_volatility
        self.kernel_confidence_threshold = kernel_confidence_threshold
        
        self.peak_value = 0
        self.volatility_indicators: Dict[Symbol, StandardDeviation] = {}
        self.kernel_indicators: Dict[Symbol, KernelRegressionIndicator] = {}
        self.current_drawdown = 0
        self.current_leverage = 0

    def Initialize(self, algorithm: QCAlgorithm, portfolio: SecurityPortfolioManager):
        for symbol in algorithm.Securities.Keys:
            self.volatility_indicators[symbol] = StandardDeviation(self.volatility_lookback)
            self.kernel_indicators[symbol] = algorithm.Indicators[f"{symbol.Value}_KernelRegression"]

    def ManageRisk(self, algorithm: QCAlgorithm, targets: List[IPortfolioTarget]) -> List[IPortfolioTarget]:
        current_value = algorithm.Portfolio.TotalPortfolioValue
        
        # Update metrics
        self._update_metrics(current_value)
        
        # Adaptive risk limits based on market regime and model confidence
        max_drawdown, max_leverage, max_volatility = self._calculate_adaptive_limits()
        
        # Check for maximum drawdown
        if self.current_drawdown > max_drawdown:
            algorithm.Log(f"Maximum drawdown of {max_drawdown:.2%} reached. Reducing all positions.")
            return self._reduce_all_positions(targets, reduction_factor=0.5)

        # Check leverage
        if self.current_leverage > max_leverage:
            algorithm.Log(f"Maximum leverage of {max_leverage} reached. Scaling back positions.")
            scale = max_leverage / self.current_leverage
            return [PortfolioTarget(target.Symbol, target.Quantity * scale) for target in targets]

        # Check individual position risks
        return self._check_individual_risks(targets, max_volatility)

    def _update_metrics(self, current_value: float):
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        self.current_drawdown = (self.peak_value - current_value) / self.peak_value
        
        total_absolute_holdings = sum(abs(holding.Quantity * holding.Price) 
                                      for holding in self.algorithm.Portfolio.Values if holding.Invested)
        self.current_leverage = total_absolute_holdings / current_value

    def _calculate_adaptive_limits(self) -> Tuple[float, float, float]:
        market_regime = self._detect_market_regime()
        model_confidence = self._assess_model_confidence()
        
        # Adjust risk limits based on market regime and model confidence
        max_drawdown = self.base_max_drawdown * (1 + 0.2 * market_regime) * (1 + 0.3 * model_confidence)
        max_leverage = self.base_max_leverage * (1 + 0.1 * market_regime) * (1 + 0.2 * model_confidence)
        max_volatility = self.base_max_volatility * (1 + 0.3 * market_regime) * (1 + 0.3 * model_confidence)
        
        return max_drawdown, max_leverage, max_volatility

    def _detect_market_regime(self) -> float:
        # Use the kernel regression to detect market regime
        # Returns a value between -1 (bearish) and 1 (bullish)
        regime_indicators = []
        for kernel_indicator in self.kernel_indicators.values():
            if kernel_indicator.IsReady:
                trend = 1 if kernel_indicator.Current.Value['trend'] == 'bullish' else -1
                regime_indicators.append(trend)
        
        return np.mean(regime_indicators) if regime_indicators else 0

    def _assess_model_confidence(self) -> float:
        # Assess the confidence of the model based on recent performance
        # Returns a value between 0 (low confidence) and 1 (high confidence)
        confidences = []
        for symbol, kernel_indicator in self.kernel_indicators.items():
            if kernel_indicator.IsReady:
                price = self.algorithm.Securities[symbol].Price
                estimate = kernel_indicator.Current.Value['estimate']
                confidence = 1 - abs(price - estimate) / price
                confidences.append(confidence)
        
        return np.mean(confidences) if confidences else 0.5

    def _check_individual_risks(self, targets: List[IPortfolioTarget], max_volatility: float) -> List[IPortfolioTarget]:
        new_targets = []
        for target in targets:
            symbol = target.Symbol
            if symbol not in self.algorithm.Securities:
                continue
            security = self.algorithm.Securities[symbol]
            if not security.HasData:
                continue

            self.volatility_indicators[symbol].Update(self.algorithm.Time, security.Price)
            current_volatility = self.volatility_indicators[symbol].Current.Value / security.Price

            if current_volatility > max_volatility:
                self.algorithm.Log(f"Volatility cap reached for {symbol}. Reducing position.")
                new_target = self._reduce_position(target, reduction_factor=0.5)
            else:
                new_target = self._adjust_position_size(target)
            
            new_targets.append(new_target)

        return new_targets

    def _reduce_all_positions(self, targets: List[IPortfolioTarget], reduction_factor: float) -> List[IPortfolioTarget]:
        return [self._reduce_position(target, reduction_factor) for target in targets]

    def _reduce_position(self, target: IPortfolioTarget, reduction_factor: float) -> IPortfolioTarget:
        new_quantity = int(target.Quantity * (1 - reduction_factor))
        return PortfolioTarget(target.Symbol, new_quantity)

    def _adjust_position_size(self, target: IPortfolioTarget) -> IPortfolioTarget:
        symbol = target.Symbol
        kernel_indicator = self.kernel_indicators[symbol]
        
        if not kernel_indicator.IsReady:
            return target
        
        confidence = kernel_indicator.Current.Value['estimate']
        if confidence > self.kernel_confidence_threshold:
            # Increase position size if confidence is high
            new_quantity = int(target.Quantity * 1.2)  # Increase by 20%
        elif confidence < (1 - self.kernel_confidence_threshold):
            # Decrease position size if confidence is low
            new_quantity = int(target.Quantity * 0.8)  # Decrease by 20%
        else:
            new_quantity = target.Quantity
        
        return PortfolioTarget(symbol, new_quantity)

    def OnSecuritiesChanged(self, algorithm: QCAlgorithm, changes: SecurityChanges):
        for added in changes.AddedSecurities:
            self.volatility_indicators[added.Symbol] = StandardDeviation(self.volatility_lookback)
            self.kernel_indicators[added.Symbol] = algorithm.Indicators[f"{added.Symbol.Value}_KernelRegression"]
        
        for removed in changes.RemovedSecurities:
            if removed.Symbol in self.volatility_indicators:
                del self.volatility_indicators[removed.Symbol]
            if removed.Symbol in self.kernel_indicators:
                del self.kernel_indicators[removed.Symbol]