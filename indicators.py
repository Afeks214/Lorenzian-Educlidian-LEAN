from AlgorithmImports import *
import numpy as np
import pandas as pd
from typing import Tuple, List

class Indicators:
    @staticmethod
    def heikin_ashi(open: np.array, high: np.array, low: np.array, close: np.array) -> Tuple[np.array, np.array, np.array, np.array]:
        ha_close = (open + high + low + close) / 4
        ha_open = np.zeros_like(open)
        ha_open[0] = open[0]
        for i in range(1, len(open)):
            ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
        ha_high = np.maximum(high, np.maximum(ha_open, ha_close))
        ha_low = np.minimum(low, np.minimum(ha_open, ha_close))
        return ha_open, ha_high, ha_low, ha_close

    @staticmethod
    def rsi(close: np.array, period: int = 14) -> np.array:
        delta = np.diff(close)
        gain, loss = delta.copy(), delta.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        avg_gain = np.convolve(gain, np.ones(period), 'valid') / period
        avg_loss = -np.convolve(loss, np.ones(period), 'valid') / period
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return np.concatenate([np.full(period, np.nan), rsi])

    @staticmethod
    def wt(high: np.array, low: np.array, close: np.array, channel_length: int = 10, average_length: int = 21) -> Tuple[np.array, np.array]:
        hlc3 = (high + low + close) / 3
        esa = Indicators.ema(hlc3, channel_length)
        d = Indicators.ema(np.abs(hlc3 - esa), channel_length)
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = Indicators.ema(ci, average_length)
        wt2 = Indicators.sma(wt1, 4)
        return wt1, wt2

    @staticmethod
    def cci(high: np.array, low: np.array, close: np.array, period: int = 20) -> np.array:
        tp = (high + low + close) / 3
        sma_tp = Indicators.sma(tp, period)
        mad = np.mean(np.abs(tp - sma_tp))
        cci = (tp - sma_tp) / (0.015 * mad)
        return cci

    @staticmethod
    def adx(high: np.array, low: np.array, close: np.array, period: int = 14) -> np.array:
        tr = np.maximum(high - low, np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1)))
        atr = Indicators.ema(tr, period)
        
        up = high - np.roll(high, 1)
        down = np.roll(low, 1) - low
        plus_dm = np.where((up > down) & (up > 0), up, 0)
        minus_dm = np.where((down > up) & (down > 0), down, 0)
        
        plus_di = 100 * Indicators.ema(plus_dm, period) / atr
        minus_di = 100 * Indicators.ema(minus_dm, period) / atr
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = Indicators.ema(dx, period)
        return adx

    @staticmethod
    def ema(data: np.array, period: int) -> np.array:
        alpha = 2 / (period + 1)
        return pd.Series(data).ewm(alpha=alpha, adjust=False).mean().values

    @staticmethod
    def sma(data: np.array, period: int) -> np.array:
        return pd.Series(data).rolling(window=period).mean().values

class IndicatorWrapper(PythonIndicator):
    def __init__(self, algorithm: QCAlgorithm, indicator_func, *args, **kwargs):
        self.algorithm = algorithm
        self.indicator_func = indicator_func
        self.args = args
        self.kwargs = kwargs
        self.Name = f"{indicator_func.__name__}_wrapper"
        self.WarmUpPeriod = kwargs.get('period', 1)
        self.Values = []

    def Update(self, input: BaseData) -> bool:
        self.Values.append(input.Value)
        if len(self.Values) < self.WarmUpPeriod:
            return False
        result = self.indicator_func(np.array(self.Values), *self.args, **self.kwargs)
        self.Current.Value = result[-1] if isinstance(result, np.ndarray) else result
        return True