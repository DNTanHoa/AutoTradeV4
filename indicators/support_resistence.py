import os
import pandas as pd
import numpy as np


def calculate_support_resistance(df, level_range=20, pip=0.0001, min_occurrence=2):
    """
    Adds support and resistance levels to the DataFrame based on price highs and lows.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'high' and 'low' columns.
    level_range : int, optional
        Approximation range for identifying support/resistance (default is 20 pips).
    pip : float, optional
        Pip unit for the currency pair (default is 0.0001).
    min_occurrence : int, optional
        Minimum occurrences for a level to be considered significant (default is 2).

    Returns
    -------
    pd.DataFrame
        Original DataFrame with additional 'support' and 'resistance' columns.
    """
    df = df.copy()
    df['support'] = np.nan
    df['resistance'] = np.nan

    lows = df['low'].tolist()
    highs = df['high'].tolist()
    current_price = df['close'].iloc[-1]  # Current close price

    # Calculate support and resistance over each row in the DataFrame
    for i in range(len(df)):
        # Get lists of lows and highs up to the current point
        list_of_lows = lows[:i + 1]
        list_of_highs = highs[:i + 1]

        # Calculate support level for the current price
        support_levels = []
        for low in list_of_lows:
            close_lows = [j for j in list_of_lows if abs(low - j) < level_range * pip]
            if len(close_lows) > min_occurrence:
                avg_support = sum(close_lows) / len(close_lows)
                if avg_support < current_price:
                    support_levels.append(avg_support)
        df.loc[df.index[i], 'support'] = max(support_levels) if support_levels else min(list_of_lows)

        # Calculate resistance level for the current price
        resistance_levels = []
        for high in list_of_highs:
            close_highs = [j for j in list_of_highs if abs(high - j) < level_range * pip]
            if len(close_highs) > min_occurrence:
                avg_resistance = sum(close_highs) / len(close_highs)
                if avg_resistance > current_price:
                    resistance_levels.append(avg_resistance)
        df.loc[df.index[i], 'resistance'] = min(resistance_levels) if resistance_levels else max(list_of_highs)

    return df
