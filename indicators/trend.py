import pandas as pd
import numpy as np


def calculate_ema(prices, period):
    """Tính đường EMA."""
    return prices.ewm(span=period, adjust=False).mean()


def adx(df, period=14):
    """ADX
    Hàm tính chỉ báo adx

    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr1 = pd.DataFrame(df['high'] - df['low'])
    tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift(1)))
    tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
    minus_di = abs(100 * (minus_dm.ewm(alpha=1 / period).mean() / atr))

    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    df['adx'] = dx.rolling(window=period).mean()

    return df


def ama(df, period=10, fast_period=2, slow_period=30):
    """AMA.
    Hàm tính chỉ báo AMA

    :param slow_period:
    :param fast_period:
    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    change = abs(df['close'] - df['close'].shift(period))
    volatility = df['close'].diff().abs().rolling(window=period).sum()

    efficiency_ratio = change / volatility
    smoothing_constant = (
            (efficiency_ratio * (2 / (fast_period + 1) - 2 / (slow_period + 1)) + 2 / (slow_period + 1)) ** 2)

    df['ama'] = np.nan
    df['ama'].iloc[period] = df['close'].iloc[:period].mean()  # Initialize the first value

    for i in range(period + 1, len(df)):
        df['ama'].iloc[i] = df['ama'].iloc[i - 1] + smoothing_constant.iloc[i] * (
                df['close'].iloc[i] - df['ama'].iloc[i - 1])

    return df


def adx_wilder(df, period=14):
    """ADX Wilder.
    Hàm tính chỉ báo ADX Wilder

    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    return adx(df, period)


def dema(df, period=20):
    """DEMA
    Hàm tính chỉ báo DEMA

    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    ema = df['close'].ewm(span=period, adjust=False).mean()
    dema = 2 * ema - ema.ewm(span=period, adjust=False).mean()

    df['dema'] = dema
    return df


def frama(df, period=10, long_period=30):
    """Fractal Adaptive Moving Average.
    Hàm tính chỉ báo Fractal Adaptive Moving Average

    :param long_period:
    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    n = len(df)
    frama = pd.Series(np.nan, index=df.index)
    for i in range(long_period, n):
        high_max = df['high'][i - long_period:i].max()
        low_min = df['low'][i - long_period:i].min()
        distance = high_max - low_min

        if distance > 0:
            alpha = (np.log(distance) - np.log(
                df['high'][i - long_period:i] - df['low'][i - long_period:i]).mean()) / np.log(2)
            alpha = 2 / (alpha + 1)
        else:
            alpha = 2 / (period + 1)

        if pd.notnull(frama[i - 1]):
            frama[i] = frama[i - 1] + alpha * (df['close'][i] - frama[i - 1])
        else:
            frama[i] = df['close'][i]

    df['frama'] = frama
    return df


def ichimoku(df):
    """Ichimoku Kinko Hyo.
    Hàm tính chỉ báo Ichimoku Kinko Hyo

    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    """
    high_9 = df['high'].rolling(window=9).max()
    low_9 = df['low'].rolling(window=9).min()
    df['tenkan_sen'] = (high_9 + low_9) / 2

    high_26 = df['high'].rolling(window=26).max()
    low_26 = df['low'].rolling(window=26).min()
    df['kijun_sen'] = (high_26 + low_26) / 2

    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)

    high_52 = df['high'].rolling(window=52).max()
    low_52 = df['low'].rolling(window=52).min()
    df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(26)

    df['chikou_span'] = df['close'].shift(-26)

    return df


def parabolic_sar(df, initial_af=0.02, step=0.02, max_af=0.2):
    """Parabolic SAR.
    Hàm tính chỉ báo Parabolic SAR

    :param max_af:
    :param step:
    :param initial_af:
    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    """
    # Parabolic SAR
    df['psar'] = df['close'][0]  # Start with the first close price
    df['psar_bull'] = df['high'][0]
    df['psar_bear'] = df['low'][0]
    df['af'] = initial_af

    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['psar'].iloc[i - 1]:
            df['psar'].iloc[i] = df['psar'].iloc[i - 1] + df['af'].iloc[i - 1] * (
                    df['psar_bull'].iloc[i - 1] - df['psar'].iloc[i - 1])
            df['psar_bull'].iloc[i] = max(df['psar_bull'].iloc[i - 1], df['high'].iloc[i])
            df['af'].iloc[i] = min(max_af, df['af'].iloc[i - 1] + step)
        else:
            df['psar'].iloc[i] = df['psar'].iloc[i - 1] - df['af'].iloc[i - 1] * (
                    df['psar'].iloc[i - 1] - df['psar_bear'].iloc[i - 1])
            df['psar_bear'].iloc[i] = min(df['psar_bear'].iloc[i - 1], df['low'].iloc[i])
            df['af'].iloc[i] = min(max_af, df['af'].iloc[i - 1] + step)

    return df


def tema(df, period=20):
    """Triple Exponential Moving Average.
    Hàm tính chỉ báo Triple Exponential Moving Average

    :param df: dataframe chứa dữ liệu giao dịch OHLCV
    :param period: chu kỳ giao dịch
    """
    # Triple Exponential Moving Average
    ema1 = df['close'].ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()

    df['tema'] = 3 * (ema1 - ema2) + ema3
    return df


def calculate_macd(df, short_period=12, long_period=26, signal_period=9):
    """
    Tính chỉ số MACD, bao gồm MACD line, Signal line, và Histogram.

    Parameters:
    df : pandas.DataFrame : DataFrame chứa dữ liệu giá với cột 'close' cho giá đóng cửa.
    short_period : int : Số chu kỳ cho EMA ngắn hạn (MACD Line).
    long_period : int : Số chu kỳ cho EMA dài hạn (MACD Line).
    signal_period : int : Số chu kỳ cho Signal Line.

    Returns:
    df : pandas.DataFrame : DataFrame có thêm các cột MACD, Signal, và Histogram.
    """
    # Tính EMA ngắn hạn và dài hạn
    df['ema_short'] = calculate_ema(df['close'], short_period)
    df['ema_long'] = calculate_ema(df['close'], long_period)

    # Tính MACD Line (EMA ngắn - EMA dài)
    df['macd_line'] = df['ema_short'] - df['ema_long']

    # Tính Signal Line (EMA của MACD Line)
    df['signal_line'] = calculate_ema(df['macd_line'], signal_period)

    # Tính MACD Histogram (MACD Line - Signal Line)
    df['macd_histogram'] = df['macd_line'] - df['signal_line']

    return df
