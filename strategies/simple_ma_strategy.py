import MetaTrader5 as mt5
import pandas as pd
import schedule
import numpy as np
import pytz
import time as t
from datetime import datetime, timedelta, time
import plotly.graph_objects as go

from mt5.data_retrieval import initialize_mt5, shutdown_mt5
from mt5.trade_execution import initialize_mt5_auth, place_order
from mt5.trade_execution import close_position
from mt5.trade_execution import get_open_positions
from mt5.trade_execution import close_all_orders
from mt5.trade_execution import close_all_buy_orders
from mt5.trade_execution import close_all_sell_orders
from mt5.trade_execution import close_all_profitable_orders
from mt5.trade_execution import update_order_sl_tp

from indicators.momentum import rsi, atr, bollinger_bands
from indicators.trend import adx
from indicators.moving_average import sma, ema, wma
from backtest.simple_back_test import calculate_sl_tp, run_simple_backtest, calculate_strategy_summary, \
    run_simple_backtest_with_daily_target, calculate_sl_tp_with_entry_price
from backtest.compound_interest_back_test import run_compound_backtest, run_compound_backtest_with_daily_target
from backtest.models.trailing_stop import TrailingStopConfig

from config.simple_ma_config import load_config, save_config, save_settings

from data.csv_database import CSVDatabase
from models.trading_signal import Signal

import sys
import logging

simple_ma_strategy_config = load_config()
db = CSVDatabase(Signal, simple_ma_strategy_config.csv_file)
is_strategy_running = False
exclude_ranges = [(time(0, 0), time(7, 0))]


def get_combine_data(symbol, timeframe_short, timeframe_long, start_date, end_date):
    """
    Lấy dữ liệu theo hai khung thời gian
    :param symbol: tài sản giao dịch.
    :param timeframe_short: khung thời gian ngắn.
    :param timeframe_long: khung thời gian dài.
    :param start_date: ngày bắt đầu.
    :param end_date: ngày kết thúc giao dịch.
    :return df_short: dữ liệu khung thời gian ngắn.
    :return df_long: dữ liệu khung thời gian dài.
    """
    if not mt5.initialize():
        print("Khởi tạo meta trader 5 thất bại, mã lỗi :", mt5.last_error())
        mt5.shutdown()
        return None, None

    # Thiết lập khoảng thời gian
    utc_from = datetime.strptime(start_date, '%Y-%m-%d')
    utc_to = datetime.strptime(end_date, '%Y-%m-%d')

    # Cào dữ liệu khung thời gian ngắn
    rates_short = mt5.copy_rates_range(symbol, timeframe_short, utc_from, utc_to)
    if rates_short is None:
        print("Không thể lấy dữ liệu cho khung thời gian ngắn, mã lỗi:", mt5.last_error())
        mt5.shutdown()
        return None, None

    # Chuyển đổi múi giờ từ UTC sang Việt Nam (GMT+7)
    vietnam_timezone = pytz.timezone('Asia/Ho_Chi_Minh')

    df_short = pd.DataFrame(rates_short)
    df_short['time'] = pd.to_datetime(df_short['time'], unit='s')
    df_short['time'] = df_short['time'].dt.tz_localize(pytz.utc).dt.tz_convert(vietnam_timezone)

    # if not df_short.empty:
    #     df_short = df_short.iloc[:-1]
    df_short['time'] = pd.to_datetime(df_short['time'], unit='s')

    # Cào dữ liệu khung thời gian dài
    rates_long = mt5.copy_rates_range(symbol, timeframe_long, utc_from, utc_to)
    if rates_long is None:
        print("Không thể lấy dữ liệu cho khung thời gian dài, mã lỗi:", mt5.last_error())
        mt5.shutdown()
        return df_short, None

    vietnam_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    df_long = pd.DataFrame(rates_long)
    df_long['time'] = pd.to_datetime(df_long['time'], unit='s')
    df_long['time'] = df_long['time'].dt.tz_localize(pytz.utc).dt.tz_convert(vietnam_timezone)

    # if not df_long.empty:
    #     df_long = df_long.iloc[:-1]
    df_long['time'] = pd.to_datetime(df_long['time'], unit='s')

    # Đóng kết nối MetaTrader 5
    mt5.shutdown()

    # Đặt cột thời gian làm chỉ mục cho cả hai DataFrame
    df_short.set_index('time', inplace=True)
    df_long.set_index('time', inplace=True)

    return df_short, df_long


def is_time_in_exclude_range(time, exclude_ranges):
    """
    Kiểm tra nếu thời gian nằm trong khoảng loại trừ.
    :param time: Thời gian cần kiểm tra (pandas.Timestamp).
    :param exclude_ranges: Danh sách các khoảng thời gian bị loại trừ (dạng tuple của thời gian bắt đầu và kết thúc).
    :return: True nếu thời gian nằm trong khoảng bị loại trừ, ngược lại False.
    """
    for start_time, end_time in exclude_ranges:
        if start_time <= time.time() <= end_time:
            return True
    return False


def calculate_technical_indicator(df, rsi_period, ma_period, atr_period=14, adx_period=14, bb_period=20):
    rsi(df, rsi_period)
    bollinger_bands(df, period=bb_period, multiplier=2)
    sma(df, ma_period)
    atr(df, atr_period)
    adx(df, adx_period)
    df['MA'] = df[f'sma_{ma_period}']
    df['RSI'] = df[f'RSI_{rsi_period}']
    return df


def generate_signal(df_long, df_short, limit, exclude_ranges,
                    rsi_long_low_threshold, rsi_short_low_threshold,
                    rsi_long_high_threshold, rsi_short_high_threshold,
                    adx_long_threshold, adx_short_threshold):
    df_long_shift = df_long

    df_short = df_short.sort_values('time')
    df_long_shift = df_long_shift.sort_values('time')

    df_merged = pd.merge_asof(df_short, df_long_shift, on='time', suffixes=('_short', '_long'))
    df_merged['Signal'] = 0
    df_merged['Signal'] = df_merged['Signal'].astype(int)
    df_merged['EntryPrice'] = 0.0
    df_merged['EntryPrice'] = df_merged['EntryPrice'].astype(float)
    df_merged['BuyCounter'] = -1
    df_merged['SellCounter'] = -1
    df_merged['LimitEntry'] = simple_ma_strategy_config.limit_entry
    df_merged['BuyCounter'] = df_merged['BuyCounter'].astype(pd.Int64Dtype())
    df_merged['SellCounter'] = df_merged['SellCounter'].astype(pd.Int64Dtype())
    df_merged['LimitEntry'] = df_merged['LimitEntry'].astype(pd.Int64Dtype())

    last_signal = 0
    counter = 0

    for i in range(1, len(df_merged)):
        close_short = df_merged['close_short'].iloc[i]
        ma_short = df_merged['MA_short'].iloc[i]
        ma_long = df_merged['MA_long'].iloc[i]
        rsi_short = df_merged['RSI_short'].iloc[i]
        adx_short = df_merged['adx_short'].iloc[i]
        time = df_merged['time'].iloc[i]

        pre_ma_long = df_merged['MA_long'].iloc[i - 1]
        pre_ma_short = df_merged['MA_short'].iloc[i - 1]
        df_merged.at[i, 'Signal'] = 0

        # Loại bỏ các tín hiệu trong khung giờ cấu hình
        if is_time_in_exclude_range(time, exclude_ranges):
            continue  # Bỏ qua tín hiệu nếu thời gian hiện tại nằm trong khoảng loại trừ

        if ((close_short > ma_short) and (close_short > pre_ma_long) and (rsi_short < rsi_short_high_threshold) and (
                adx_short > adx_short_threshold)):
            if last_signal != 1:
                last_signal = 1
                counter = 0
            if counter < limit:
                df_merged.at[i, 'Signal'] = 1  # Tín hiệu mua
                df_merged.at[i, 'BuyCounter'] = counter
                df_merged.at[i, 'LimitEntry'] = limit
                counter = counter + 1

        if ((close_short < ma_short) and (close_short < pre_ma_long) and (rsi_short > rsi_short_low_threshold) and (
                adx_short > adx_short_threshold)):
            if last_signal != -1:
                last_signal = -1
                counter = 0
            if counter < limit:
                df_merged.at[i, 'Signal'] = -1  # Tín hiệu bán
                df_merged.at[i, 'SellCounter'] = counter
                df_merged.at[i, 'LimitEntry'] = limit
                counter = counter + 1
    return df_merged


def process_trailing_stop(position, signal, last_price, symbol_lot_standard, tp_price):
    shifts_config = [
        {"shift": "first_shift", "price_shift": 1, "sl_multiplier": 0.7, "tp_multiplier": 1.5},
        {"shift": "second_shift", "price_shift": 2, "sl_multiplier": 1.5, "tp_multiplier": 1.5},
        {"shift": "third_shift", "price_shift": 3, "sl_multiplier": 2.3, "tp_multiplier": 1.5},
        {"shift": "fourth_shift", "price_shift": 4, "sl_multiplier": 3.5, "tp_multiplier": 1.5},
        {"shift": "fifth_shift", "price_shift": 5, "sl_multiplier": 4, "tp_multiplier": 1.5},
        {"shift": "sixth_shift", "price_shift": 6, "sl_multiplier": 5, "tp_multiplier": 1.5},
        {"shift": "seventh_shift", "price_shift": 8, "sl_multiplier": 6, "tp_multiplier": 1.5},
    ]

    if signal['signal'] == "1":  # Tín hiệu Buy
        for config in shifts_config:
            if last_price > position.price_open + config["price_shift"] * symbol_lot_standard and '' == signal[
                config["shift"]]:
                new_sl_price = position.price_open + config["sl_multiplier"] * symbol_lot_standard
                new_tp_price = position.tp + config["tp_multiplier"] * symbol_lot_standard
                # update order
                update_order_sl_tp(position.ticket, new_sl_price, new_tp_price)
                # update signal
                signal[config["shift"]] = 'True'
                signal[f"{config['shift']}_sl"] = new_sl_price
                signal[f"{config['shift']}_tp"] = new_tp_price
                db.update_row('order_id', str(position.ticket), signal)

    elif signal['signal'] == "-1":  # Tín hiệu Sell
        for config in shifts_config:
            if last_price < position.price_open - config["price_shift"] * symbol_lot_standard and signal[
                config["shift"]] == '':
                new_sl_price = position.price_open - config["sl_multiplier"] * symbol_lot_standard
                new_tp_price = position.tp - config["tp_multiplier"] * symbol_lot_standard
                # update order
                update_order_sl_tp(position.ticket, new_sl_price, new_tp_price)
                # update signal
                signal[config["shift"]] = 'True'
                signal[f"{config['shift']}_sl"] = new_sl_price
                signal[f"{config['shift']}_tp"] = new_tp_price
                db.update_row('order_id', str(position.ticket), signal)


def run_market_analysis():
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Market analysis start running........")

        # Khai báo biến global để sử dụng
        global simple_ma_strategy_config
        global exclude_ranges

        # ------ Step 1: Lấy dữ liệu ------ #
        end_date = (datetime.now().date() + timedelta(days=3)).strftime('%Y-%m-%d')
        start_date = (datetime.now().date() - timedelta(days=8)).strftime('%Y-%m-%d')
        df_short, df_long = get_combine_data(simple_ma_strategy_config.symbol,
                                             simple_ma_strategy_config.timeframe_short,
                                             simple_ma_strategy_config.timeframe_long,
                                             start_date, end_date)

        if df_short is None or df_long is None:
            print("Có lỗi xảy ra trong quá trình cào dữ liệu.")
            print(f"{timestamp} Market analysis finishedfinished (after error).........")
            return

        # ------ Step 2: Tính toán chỉ báo kỹ thuật ------ #
        calculate_technical_indicator(df_short,
                                      simple_ma_strategy_config.rsi_short_period,
                                      simple_ma_strategy_config.ma_short_period,
                                      simple_ma_strategy_config.atr_short_period,
                                      simple_ma_strategy_config.adx_short_period,
                                      simple_ma_strategy_config.bb_short_period)
        calculate_technical_indicator(df_long,
                                      simple_ma_strategy_config.rsi_long_period,
                                      simple_ma_strategy_config.ma_long_period,
                                      simple_ma_strategy_config.atr_long_period,
                                      simple_ma_strategy_config.adx_long_period,
                                      simple_ma_strategy_config.bb_long_period)

        # ------ Step 3: Xác định tín hiệu buy hoặc sell & điểm SL và TP ------ #
        df_signals = generate_signal(df_long, df_short, simple_ma_strategy_config.limit_entry,
                                     exclude_ranges=exclude_ranges,
                                     rsi_long_low_threshold=30,
                                     rsi_short_low_threshold=30,
                                     rsi_long_high_threshold=70,
                                     rsi_short_high_threshold=70,
                                     adx_long_threshold=10,
                                     adx_short_threshold=10)
        last_signal = df_signals.loc[df_signals['time'].idxmax()]

        print("*** ---------------------------------------------- ***")
        print(f"*\tLast signal is {last_signal['time']}\n"
              f"*\tMA Short: {last_signal['MA_short']}\n"
              f"*\tClose Short: {last_signal['close_short']}\n"
              f"*\tMA Long: {last_signal['MA_long']}\n"
              f"*\tClose Long: {last_signal['close_long']}\n"
              f"*\tRSI Short: {last_signal['RSI_short']}\n"
              f"*\tRSI Long: {last_signal['RSI_long']}\n"
              f"*\tADX Short: {last_signal['adx_short']}\n"
              f"*\tADX Long: {last_signal['adx_long']}\n"
              f"*\tLast Signal: {last_signal['Signal']}")
        print("*** ---------------------------------------------- ***")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df_signals = calculate_sl_tp(df_signals, simple_ma_strategy_config.min_sl,
                                     simple_ma_strategy_config.min_tp,
                                     simple_ma_strategy_config.lot_standard)

        last_signal = df_signals.loc[df_signals['time'].idxmax()]
        entry_price = last_signal['close']
        sl_price = last_signal['SL']
        tp_price = last_signal['TP']
        buy_counter = last_signal['BuyCounter']
        sell_counter = last_signal['SellCounter']
        limit = last_signal['LimitEntry']

        # ------ Step 4: Xác định tín hiệu ở cây nến cuối ------ #
        if last_signal['Signal'] == 0:
            # Chờ quan sát
            print(f'{timestamp} Không có điểm vào lệnh chờ quan sát tiếp')
            print(f"{timestamp} Market analysis finished........")
            return
        else:
            signal_key = last_signal['time'].strftime('%Y%m%d%H%M')
            first_signal = db.get_first_row_by_key('signal_key', signal_key)
            is_signal_processed = first_signal != None

            # Kiểm tra xem tín hiệu đã được phát chưa
            if is_signal_processed:
                signal_type = "Buy" if last_signal['Signal'] == 1 else "Sell"
                print(f"Tín hiệu {signal_type} đã được phát trước đó.......")
            else:
                signal_data = Signal(
                    signal_key=signal_key,
                    timestamp=timestamp,
                    symbol=simple_ma_strategy_config.symbol,
                    signal=last_signal['Signal'],
                    entry=entry_price,
                    sl=sl_price,
                    tp=tp_price,
                    limit_entry=limit,
                    sell_counter=sell_counter,
                    buy_counter=buy_counter,
                    processed=False
                )
                db.insert_row(signal_data.dict())

                if last_signal['Signal'] == 1:
                    # Tín hiệu buy
                    print(f"Xuất hiện tín hiệu mua - Điểm vào lệnh: {entry_price}. SL: {sl_price}. TP: {tp_price}")
                elif last_signal['Signal'] == -1:
                    # Tín hiệu buy
                    print(f"Xuất hiện tín hiệu bán - Điểm vào lệnh: {entry_price}. SL: {sl_price}. TP: {tp_price}")

            print(f"{timestamp} Market analysis finished........")
    except Exception as e:
        # Catch all exceptions and handle them
        print(f"An error occurred: {str(e)}")
        # Optionally, assign a default value to timestamp if it was not initialized
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Market analysis finishedfinished (after error).........")
    return
