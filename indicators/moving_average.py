import pandas as pd
import numpy as np


def sma(df, period):
    df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
    return df


def ema(df, period):
    df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df


def wma(df, period):
    weights = pd.Series(range(1, period + 1))
    df[f'wma_{period}'] = df['close'].rolling(window=period).apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw=True)
    return df


def calculate_ema(prices, period):
    """Tính đường EMA."""
    return prices.ewm(span=period, adjust=False).mean()
