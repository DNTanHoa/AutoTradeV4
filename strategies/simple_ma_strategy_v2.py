import MetaTrader5 as mt5
import pandas as pd
import schedule
import numpy as np
import pytz
import time as t
from datetime import datetime, timedelta, time
import plotly.graph_objects as go

from mt5.data_retrieval import initialize_mt5, shutdown_mt5, check_position_exists, check_last_closed_position_type
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


def get_history_data(symbol, timeframe, start_date, end_date, is_include_last):
    if not mt5.initialize():
        print("Khởi tạo meta trader 5 thất bại, mã lỗi :", mt5.last_error())
        mt5.shutdown()
        return None

    # Thiết lập khoảng thời gian
    utc_from = datetime.strptime(start_date, '%Y-%m-%d')
    utc_to = datetime.strptime(end_date, '%Y-%m-%d')

    # Cào dữ liệu theo khung thời gian
    rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)
    if rates is None:
        print("Không thể lấy dữ liệu cho khung thời gian tương ứng, mã lỗi:", mt5.last_error())
        mt5.shutdown()
        return None

    # Chuyển đổi múi giờ từ UTC sang Việt Nam (GMT+7)
    vietnam_timezone = pytz.timezone('Asia/Ho_Chi_Minh')

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['time'] = df['time'].dt.tz_localize(pytz.utc).dt.tz_convert(vietnam_timezone)

    if not is_include_last and not df.empty:
        df = df.iloc[:-1]

    return df


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


def calculate_technical_indicator(df, rsi_period, ma_period):
    rsi(df, rsi_period)
    sma(df, ma_period)
    df['MA'] = df[f'sma_{ma_period}']
    df['RSI'] = df[f'RSI_{rsi_period}']
    return df


def calculate_technical_indicator_v2(df, rsi_period, ma_period):
    rsi(df, rsi_period)
    ema(df, ma_period)
    df['MA'] = df[f'ema_{ma_period}']
    df['RSI'] = df[f'RSI_{rsi_period}']
    return df


def generate_signal(df_long, df_short, limit, exclude_ranges,
                    rsi_long_low_threshold, rsi_short_low_threshold,
                    rsi_long_high_threshold, rsi_short_high_threshold):
    # ------ Step 1: Lấy dữ liệu dòng cuối cùng------ #
    last_short = df_short.iloc[-1]
    last_long = df_long.iloc[-1]

    df_short['Signal'] = 0
    df_short['Signal'] = df_short['Signal'].astype(int)
    df_short['entry_price'] = 0.0
    df_short['entry_price'] = df_short['entry_price'].astype(float)
    df_short['SL'] = 0.0
    df_short['SL'] = df_short['SL'].astype(float)
    df_short['TP'] = 0.0
    df_short['TP'] = df_short['TP'].astype(float)

    # ------ Step 2: Lấy dữ liệu dòng cuối cùng và check thời gian giao dịch------ #
    time = df_short['time'].iloc[-1]

    # ------ Step 3: Xác định tín hiệu giao dịch ở điểm cuối------ #
    if not is_time_in_exclude_range(time, exclude_ranges):
        if last_short['close'] > last_short['MA'] and last_long['close'] > last_long['MA']:
            df_short.iloc[-1, df_short.columns.get_loc('Signal')] = 1     # Tín hiệu buy
            df_short.iloc[-1, df_short.columns.get_loc('entry_price')] = last_short['close']
            df_short.iloc[-1, df_short.columns.get_loc('SL')] = last_short['close'] - simple_ma_strategy_config.min_sl
            df_short.iloc[-1, df_short.columns.get_loc('TP')] = last_short['close'] + simple_ma_strategy_config.min_tp
        elif last_short['close'] < last_short['MA'] and last_long['close'] < last_long['MA']:
            df_short.iloc[-1, df_short.columns.get_loc('Signal')] = -1    # Tín hiệu sell
            df_short.iloc[-1, df_short.columns.get_loc('entry_price')] = last_short['close']
            df_short.iloc[-1, df_short.columns.get_loc('SL')] = last_short['close'] + simple_ma_strategy_config.min_sl
            df_short.iloc[-1, df_short.columns.get_loc('TP')] = last_short['close'] - simple_ma_strategy_config.min_tp
        else:
            df_short.iloc[-1, df_short.columns.get_loc('Signal')] = 0     # Không có tín hiệu
        return df_short

    return df_short


def check_same_signal(last_n_rows: list, signal_to_check: str) -> bool:
    """
    Kiểm tra xem tất cả các dòng trong last_n_rows có cùng giá trị signal hay không.

    Args:
        last_n_rows (list): Danh sách chứa các dòng dữ liệu để kiểm tra.

    Returns:
        bool: True nếu tất cả các dòng có cùng giá trị signal, False nếu ngược lại.
    """
    if not last_n_rows:
        return False  # Danh sách trống

    # Kiểm tra nếu tất cả các dòng đều có giá trị signal giống nhau
    return all(row['signal'] == signal_to_check for row in last_n_rows)


def process_trailing_stop(position, signal, last_price, symbol_lot_standard, tp_price):
    shifts_config = [
        {"shift": "second_shift", "price_shift": 2, "sl_multiplier": 1, "tp_multiplier": 1},
        {"shift": "third_shift", "price_shift": 3, "sl_multiplier": 2, "tp_multiplier": 1.5},
        {"shift": "fourth_shift", "price_shift": 4, "sl_multiplier": 3, "tp_multiplier": 1.5},
        {"shift": "fifth_shift", "price_shift": 5, "sl_multiplier": 4, "tp_multiplier": 1},
        {"shift": "sixth_shift", "price_shift": 6, "sl_multiplier": 5, "tp_multiplier": 1},
        {"shift": "seventh_shift", "price_shift": 7, "sl_multiplier": 6, "tp_multiplier": 1},
    ]

    if signal['signal'] == "1":  # Tín hiệu Buy
        for config in shifts_config:
            if last_price > position.price_open + config["price_shift"] * symbol_lot_standard and '' == signal[config["shift"]]:
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
            if last_price < position.price_open - config["price_shift"] * symbol_lot_standard and signal[config["shift"]] == '':
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

        df_short = get_history_data(simple_ma_strategy_config.symbol,
                                    simple_ma_strategy_config.timeframe_short,
                                    start_date, end_date, False)
        df_long = get_history_data(simple_ma_strategy_config.symbol,
                                   simple_ma_strategy_config.timeframe_long,
                                   start_date, end_date, True)

        # ------ Step 2: Tính toán chỉ báo kỹ thuật ------ #
        calculate_technical_indicator(df_short, simple_ma_strategy_config.rsi_short_period,
                                      simple_ma_strategy_config.ma_short_period)
        calculate_technical_indicator(df_long, simple_ma_strategy_config.rsi_long_period,
                                      simple_ma_strategy_config.ma_long_period)

        # ------ Step 3: Xác định tín hiệu buy hoặc sell & điểm SL và TP ------ #
        df_signals = generate_signal(df_long, df_short, simple_ma_strategy_config.limit_entry,
                                     exclude_ranges=exclude_ranges,
                                     rsi_long_low_threshold=30,
                                     rsi_short_low_threshold=30,
                                     rsi_long_high_threshold=70,
                                     rsi_short_high_threshold=70)

        last_signal = df_signals.iloc[-1]

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

        last_signal = df_signals.loc[df_signals['time'].idxmax()]
        entry_price = last_signal['entry_price']
        sl_price = last_signal['SL']
        tp_price = last_signal['TP']

        # ------ Step 4: Xác định tín hiệu ở cây nến cuối ------ #
        if last_signal['Signal'] == 0:
            # Chờ quan sát
            print(f'{timestamp} Không có điểm vào lệnh chờ quan sát tiếp')
            print(f"{timestamp} Market analysis finished........")
            return
        else:
            signal_key = last_signal['time'].strftime('%Y%m%d%H%M')
            first_signal = db.get_first_row_by_key('signal_key', signal_key)
            is_signal_processed = first_signal is not None
            signal_type = "Buy" if last_signal['Signal'] == 1 else "Sell"

            # Kiểm tra xem tín hiệu đã được phát chưa
            if is_signal_processed:
                print(f"Tín hiệu {signal_type} đã được phát trước đó.......")
            else:
                old_signals = db.get_last_n_rows(simple_ma_strategy_config.limit_entry)
                if check_same_signal(old_signals, str(last_signal['Signal'])):
                    print(f"Tín hiệu {signal_type} đã đạt limit entry")
                else:
                    signal_data = Signal(
                        signal_key=signal_key,
                        timestamp=timestamp,
                        symbol=simple_ma_strategy_config.symbol,
                        signal=last_signal['Signal'],
                        entry=entry_price,
                        sl=sl_price,
                        tp=tp_price,
                        limit_entry=simple_ma_strategy_config.limit_entry,
                        sell_counter=0,
                        buy_counter=0,
                        processed=False
                    )
                    db.insert_row(signal_data.model_dump())
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
        print(f"{timestamp} Market analysis finished (after error).........")
    return


def run_market_execution():
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Market analysis start running........")

        # ------ Step 1: Lấy tất cả lệnh chưa xử lý trong file csv ------ #
        unprocessed_orders = db.get_unprocessed_rows()
        if not unprocessed_orders:
            print('{0} Không có lệnh cần xử lý......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # ------ Step 2: Duyệt qua và xử lý lệnh ------ #
        else:
            for signal in unprocessed_orders:
                signal_key = signal['signal_key']
                signal_type = int(signal['signal'])
                entry_price = float(signal['entry'])
                sl_price = float(signal['sl'])
                tp_price = float(signal['tp'])
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                volume = simple_ma_strategy_config.volume

                if signal_type == 1:  # Tín hiệu buy
                    if (initialize_mt5_auth(simple_ma_strategy_config.login,
                                            simple_ma_strategy_config.password,
                                            simple_ma_strategy_config.server)):
                        print('{0} Đóng tất cả lệnh SELL......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        close_all_sell_orders()

                        print(f"Thực hiện lệnh BUY tại giá {entry_price}, SL: {sl_price}, TP: {tp_price}")
                        buy_result = place_order(simple_ma_strategy_config.symbol, volume, 'buy', entry_price, sl_price,
                                                 tp_price, signal_key)
                        shutdown_mt5()

                        if buy_result.retcode == mt5.TRADE_RETCODE_DONE:
                            signal['order_id'] = buy_result.order
                            print(f"Thực hiện lệnh BUY thành công với mã order {buy_result.order}")
                    else:
                        print(f'{timestamp} Lỗi khởi tạo MT5......')
                elif signal_type == -1:  # Tín hiệu sell
                    if (initialize_mt5_auth(simple_ma_strategy_config.login,
                                            simple_ma_strategy_config.password,
                                            simple_ma_strategy_config.server)):
                        print('{0} Đóng tất cả lệnh BUY......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        close_all_buy_orders()

                        print(f"Thực hiện lệnh SELL tại giá {entry_price}, SL: {sl_price}, TP: {tp_price}")
                        sell_result = place_order(simple_ma_strategy_config.symbol, volume, 'sell', entry_price,
                                                  sl_price, tp_price, signal_key)
                        shutdown_mt5()

                        if sell_result.retcode == mt5.TRADE_RETCODE_DONE:
                            signal['order_id'] = sell_result.order
                            print(f"Thực hiện lệnh SELL thành công với mã order {sell_result.order}")
                    else:
                        print(f'{timestamp} Lỗi khởi tạo MT5......')
                # ------ Step 3: Cập nhật lệnh ------ #
                signal['processed'] = 'True'
                signal['lot_size'] = volume
                db.update_row('signal_key', signal_key, signal)

        shutdown_mt5()
        print(f"{timestamp} Market execution finished.........")
    except Exception as e:
        # Catch all exceptions and handle them
        print(f"An error occurred: {str(e)}")
        # Optionally, assign a default value to timestamp if it was not initialized
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Market execution finished (after error).........")
    return


def run_risk_management():
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Risk management start running........")
        global simple_ma_strategy_config  # Khai báo biến global để sử dụng

        if (not initialize_mt5_auth(simple_ma_strategy_config.login,
                                    simple_ma_strategy_config.password,
                                    simple_ma_strategy_config.server)):
            print("MT5 initialization failed")

        # ------ Step 1: Lấy tất cả lệnh đang mở trên tài khoản ------ #
        get_open_result = get_open_positions()
        if not (get_open_result['success'] == True):
            print(f'{timestamp} Lấy vị thế lệnh mở thất bại')
            print(f'{timestamp} Risk management finished......')
            shutdown_mt5()
            return

        positions = get_open_result['positions']
        if positions is None or len(positions) == 0:
            print(f'{timestamp} Không có lệnh đang mở trên tài khoản')
            print('{0} Order monitor finished......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            shutdown_mt5()
            return

        # ------ Step 2: Duyệt qua các vị thế mở và kiểm tra với giá ------ #
        end_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        utc_from = datetime.strptime(start_date, '%Y-%m-%d')
        utc_to = datetime.strptime(end_date, '%Y-%m-%d')
        rates = mt5.copy_rates_range(simple_ma_strategy_config.symbol,
                                     simple_ma_strategy_config.timeframe_short, utc_from, utc_to)

        if rates is None:
            print("Không thể lấy dữ liệu cho khung thời gian ngắn, mã lỗi:", mt5.last_error())
            print(f"{timestamp} Risk management finished......")
            mt5.shutdown()
            return

        # ------ Step 3: Kiểm tra giá và dời SL/TP ------ #
        vietnam_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['time'] = df['time'].dt.tz_localize(pytz.utc).dt.tz_convert(vietnam_timezone)

        if not df.empty:
            df = df.iloc[:-1]

        last_data = df.iloc[-1]
        last_price = last_data['close']

        for position in positions:
            # Lấy thông tin signal từ database bằng order_id
            signal = db.get_first_row_by_key('order_id', str(position.ticket))

            if signal is None:
                print("Không thể tìm thấy lệnh trong dữ liệu đã lưu:")
                print('{0} Order monitor finished......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                mt5.shutdown()
                continue

            signal_type = int(signal['signal'])
            entry_price = float(signal['entry'])
            sl_price = float(signal['sl'])
            tp_price = float(signal['tp'])

            process_trailing_stop(position=position, signal=signal, last_price=last_price,
                                  symbol_lot_standard=simple_ma_strategy_config.lot_standard, tp_price=tp_price)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} Risk management finished.........")
    except Exception as e:
        # Catch all exceptions and handle them
        print(f"An error occurred: {str(e)}")
        # Optionally, assign a default value to timestamp if it was not initialized
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} Risk management finished (after error).........")
    return


def run_simple_ma_strategy_v2():
    print('{0} Strategy start running......'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    schedule.every(1).seconds.do(run_market_analysis)
    schedule.every(1).seconds.do(run_market_execution)
    schedule.every(1).seconds.do(run_risk_management)

    while True:
        schedule.run_pending()  # Chỉ chạy khi schedule_running = True
        t.sleep(1)
    return


def start_strategy():
    global is_strategy_running
    is_strategy_running = True
    return


def stop_strategy():
    global is_strategy_running
    is_strategy_running = False
    return
