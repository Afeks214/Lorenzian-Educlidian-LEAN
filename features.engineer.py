# region imports
from AlgorithmImports import *
# endregion
# features/engineer.py

import numpy as np
import pandas as pd
from typing import Dict

class FeatureEngineer:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def create_features(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        features = {}
        for symbol, df in data.items():
            features[symbol] = self._engineer_symbol_features(df)
        return features

    def _engineer_symbol_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Basic price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Technical indicators
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_30'] = df['close'].rolling(window=30).mean()
        df['rsi'] = self._calculate_rsi(df['close'], window=14)
        df['macd'], df['signal'], df['hist'] = self._calculate_macd(df['close'])
        
        # Volatility
        df['atr'] = self._calculate_atr(df['high'], df['low'], df['close'], window=14)
        
        return df.dropna()

    def _calculate_rsi(self, prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _calculate_atr(self, high, low, close, window=14):
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()# region imports
from AlgorithmImports import *
# endregion
# features/engineer.py

import numpy as np
import pandas as pd
from typing import Dict

class FeatureEngineer:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def create_features(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        features = {}
        for symbol, df in data.items():
            features[symbol] = self._engineer_symbol_features(df)
        return features

    def _engineer_symbol_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Basic price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Technical indicators
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_30'] = df['close'].rolling(window=30).mean()
        df['rsi'] = self._calculate_rsi(df['close'], window=14)
        df['macd'], df['signal'], df['hist'] = self._calculate_macd(df['close'])
        
        # Volatility
        df['atr'] = self._calculate_atr(df['high'], df['low'], df['close'], window=14)
        
        return df.dropna()

    def _calculate_rsi(self, prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _calculate_atr(self, high, low, close, window=14):
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()