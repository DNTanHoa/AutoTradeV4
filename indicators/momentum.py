from typing import Any

import numpy as np
import pandas as pd
from numpy import ndarray, dtype


# Hàm tính chỉ báo rsi
def rsi(df, period=14):
    # Tính sự thay đổi giá (Price changes)
    delta = df['close'].diff()

    # Tách positive gains (lợi nhuận dương) và negative losses (lỗ)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    # Tính trung bình đầu tiên bằng SMA cho chu kỳ đầu tiên
    avg_gain = np.zeros_like(gain)
    avg_loss = np.zeros_like(loss)

    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])

    # Áp dụng phương pháp làm mượt (smoothing) tương tự như EMA cho các chu kỳ tiếp theo
    for i in range(period + 1, len(gain)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period

    # Tính RS (Relative Strength)
    rs = np.zeros_like(avg_loss)
    non_zero_loss = avg_loss != 0
    rs[non_zero_loss] = avg_gain[non_zero_loss] / avg_loss[non_zero_loss]
    rs[~non_zero_loss] = np.nan  # Handle cases where avg_loss == 0

    # Tính RSI theo công thức RSI = 100 - (100 / (1 + RS))
    rsi: ndarray[Any, dtype[Any]] = 100 - (100 / (1 + rs))

    # Thêm chỉ số RSI vào DataFrame
    df[f'RSI_{period}'] = rsi

    return df


def bollinger_bands(df, period=20, multiplier=2):
    """
    Tính dải Bollinger Bands cho một DataFrame.

    Args:
        df (pd.DataFrame): DataFrame chứa giá đóng cửa ('close').
        period (int): Số chu kỳ để tính SMA và độ lệch chuẩn (mặc định là 20).
        multiplier (int): Hệ số nhân độ lệch chuẩn (mặc định là 2).

    Returns:
        pd.DataFrame: DataFrame chứa cột Bollinger Bands (middle, upper, lower).
    """
    # Tính đường trung bình động đơn giản (SMA)
    df['MID'] = df['close'].rolling(window=period).mean()

    # Tính độ lệch churn của giá đóng cửa trong khoảng thời gian 'period'
    df['STD'] = df['close'].rolling(window=period).std()

    # Tính dải trên (upper band)
    df['Upper'] = df['MID'] + (multiplier * df['STD'])

    # Tính dải dưới (lower band)
    df['Lower'] = df['MID'] - (multiplier * df['STD'])

    # Trả về DataFrame với Bollinger Bands
    return df[['MID', 'Upper', 'Lower']]


# Hàm tính True Range (TR)
def calculate_true_range(data):
    data['previous_close'] = data['close'].shift(1)
    data['TR1'] = data['high'] - data['low']
    data['TR2'] = abs(data['high'] - data['previous_close'])
    data['TR3'] = abs(data['low'] - data['previous_close'])
    data['True_Range'] = data[['TR1', 'TR2', 'TR3']].max(axis=1)
    return data


# Hàm tính Average True Range (ATR)
def atr(data, period=14):
    data = calculate_true_range(data)
    data['atr'] = data['True_Range'].rolling(window=period).mean()
    return data
