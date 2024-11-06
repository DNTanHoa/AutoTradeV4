import numpy as np
import pandas as pd


def calculate_trendlines(data, length=14, mult=1.0, method='Atr'):
    """
    Hàm tính toán các trendline kháng cự và hỗ trợ với điểm phá vỡ dựa trên chỉ báo LuxAlgo.

    Parameters:
    - data (DataFrame): Dữ liệu OHLCV với các cột ['open', 'high', 'low', 'close', 'volume']
    - length (int): Số chu kỳ để tính đỉnh/đáy.
    - mult (float): Hệ số điều chỉnh slope.
    - method (str): Phương pháp tính slope ('Atr', 'Stdev', 'Linreg').

    Returns:
    - DataFrame: Dữ liệu với cột trendline kháng cự và hỗ trợ, cùng các tín hiệu phá vỡ.
    """
    df = data.copy()

    # Tính Pivot High và Pivot Low
    df['pivot_high'] = df['high'][(df['high'] == df['high'].rolling(window=length * 2 + 1, center=True).max())]
    df['pivot_low'] = df['low'][(df['low'] == df['low'].rolling(window=length * 2 + 1, center=True).min())]

    # Tính slope dựa trên phương pháp được chọn
    if method == 'Atr':
        df['slope'] = df['high'].rolling(window=length).apply(lambda x: np.ptp(x) / length) * mult
    elif method == 'Stdev':
        df['slope'] = df['close'].rolling(window=length).std() / length * mult
    elif method == 'Linreg':
        x = np.arange(length)
        df['slope'] = df['close'].rolling(window=length).apply(lambda y: np.polyfit(x, y, 1)[0]) * mult

    # Khởi tạo các trendline
    df['upper'] = np.nan
    df['lower'] = np.nan
    df['upos'] = 0
    df['dnos'] = 0

    # Khởi tạo các biến slope
    slope_ph = 0
    slope_pl = 0

    # Tính các mức kháng cự và hỗ trợ
    for i in range(len(df)):
        if not np.isnan(df['pivot_high'].iloc[i]):
            slope_ph = df['slope'].iloc[i]
            df['upper'].iloc[i] = df['pivot_high'].iloc[i]
        else:
            df['upper'].iloc[i] = df['upper'].iloc[i - 1] - slope_ph if i > 0 else np.nan

        if not np.isnan(df['pivot_low'].iloc[i]):
            slope_pl = df['slope'].iloc[i]
            df['lower'].iloc[i] = df['pivot_low'].iloc[i]
        else:
            df['lower'].iloc[i] = df['lower'].iloc[i - 1] + slope_pl if i > 0 else np.nan

        # Tính điểm phá vỡ
        df['upos'].iloc[i] = 1 if (df['close'].iloc[i] > df['upper'].iloc[i] - slope_ph * length) else 0
        df['dnos'].iloc[i] = 1 if (df['close'].iloc[i] < df['lower'].iloc[i] + slope_pl * length) else 0

    # Tín hiệu phá vỡ trendline
    df['upper_break'] = df.apply(lambda row: row['low'] if row['upos'] > row['upos'].shift(1) else np.nan, axis=1)
    df['lower_break'] = df.apply(lambda row: row['high'] if row['dnos'] > row['dnos'].shift(1) else np.nan, axis=1)

    return df
