from AlgorithmImports import *
import numpy as np
from typing import Dict, Any

class NadarayaWatsonRationalQuadratic:
    def __init__(self, algorithm: QCAlgorithm, lookback_window: float = 8.0, relative_weighting: float = 8.0, 
                 start_bar: int = 25, smooth_colors: bool = False, lag: int = 2):
        self.algorithm = algorithm
        self.lookback_window = lookback_window
        self.relative_weighting = relative_weighting
        self.start_bar = start_bar
        self.smooth_colors = smooth_colors
        self.lag = lag
        
        self.c_bullish = '#3AFF17'  # Green
        self.c_bearish = '#FD1707'  # Red
        
        self.data_window = RollingWindow[float](start_bar + 1)

    def kernel_regression(self, source: np.ndarray, h: float) -> np.ndarray:
        size = len(source)
        yhat = np.zeros(size)
        
        for i in range(size):
            if i < self.start_bar:
                yhat[i] = np.nan
            else:
                current_weight = 0.0
                cumulative_weight = 0.0
                for j in range(i + 1):
                    y = source[j]
                    w = (1 + (j ** 2 / ((h ** 2) * 2 * self.relative_weighting))) ** -self.relative_weighting
                    current_weight += y * w
                    cumulative_weight += w
                yhat[i] = current_weight / cumulative_weight
        
        return yhat

    def calculate(self) -> Dict[str, Any]:
        source = np.array([x for x in self.data_window])[::-1]
        size = len(source)
        
        yhat1 = self.kernel_regression(source, self.lookback_window)
        yhat2 = self.kernel_regression(source, self.lookback_window - self.lag)
        
        is_bearish = np.zeros(size, dtype=bool)
        is_bullish = np.zeros(size, dtype=bool)
        is_bearish_change = np.zeros(size, dtype=bool)
        is_bullish_change = np.zeros(size, dtype=bool)
        
        for i in range(2, size):
            is_bearish[i] = yhat1[i-1] > yhat1[i]
            is_bullish[i] = yhat1[i-1] < yhat1[i]
            is_bearish_change[i] = is_bearish[i] and (yhat1[i-2] < yhat1[i-1])
            is_bullish_change[i] = is_bullish[i] and (yhat1[i-2] > yhat1[i-1])
        
        is_bullish_cross = np.zeros(size, dtype=bool)
        is_bearish_cross = np.zeros(size, dtype=bool)
        
        for i in range(1, size):
            is_bullish_cross[i] = yhat2[i] > yhat1[i] and yhat2[i-1] <= yhat1[i-1]
            is_bearish_cross[i] = yhat2[i] < yhat1[i] and yhat2[i-1] >= yhat1[i-1]
        
        is_bullish_smooth = yhat2 > yhat1
        is_bearish_smooth = yhat2 < yhat1
        
        color_by_cross = np.where(is_bullish_smooth, self.c_bullish, self.c_bearish)
        color_by_rate = np.where(is_bullish, self.c_bullish, self.c_bearish)
        plot_color = color_by_cross if self.smooth_colors else color_by_rate
        
        alert_bullish = is_bearish_cross if self.smooth_colors else is_bearish_change
        alert_bearish = is_bullish_cross if self.smooth_colors else is_bullish_change
        
        alert_stream = np.where(alert_bearish, -1, np.where(alert_bullish, 1, 0))
        
        return {
            'yhat1': yhat1,
            'yhat2': yhat2,
            'plot_color': plot_color,
            'alert_bullish': alert_bullish,
            'alert_bearish': alert_bearish,
            'alert_stream': alert_stream
        }

    def update(self, new_data: float) -> Dict[str, Any]:
        self.data_window.Add(new_data)
        return self.calculate()

    def get_signals(self, results: Dict[str, Any]) -> Dict[str, Any]:
        last_index = -1
        return {
            'trend': 'bullish' if results['plot_color'][last_index] == self.c_bullish else 'bearish',
            'alert': results['alert_stream'][last_index],
            'estimate': results['yhat1'][last_index]
        }

class KernelRegressionIndicator(PythonIndicator):
    def __init__(self, algorithm: QCAlgorithm, symbol: Symbol):
        self.algorithm = algorithm
        self.symbol = symbol
        self.nw = NadarayaWatsonRationalQuadratic(algorithm)
        self.Name = f"{self.symbol.Value}_KernelRegression"

    def Update(self, input: BaseData) -> bool:
        if not input.Symbol == self.symbol:
            return False
        
        results = self.nw.update(input.Value)
        signals = self.nw.get_signals(results)
        
        self.algorithm.Plot(self.Name, "Estimate", results['yhat1'][-1])
        self.algorithm.Plot(self.Name, "Price", input.Value)
        
        return True