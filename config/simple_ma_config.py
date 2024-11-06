import json
import MetaTrader5 as mt5
from types import SimpleNamespace


# Tạo hàm để chuyển đổi từ số sang khung thời gian của MT5
def convert_timeframe_to_mt5(value):
    timeframes = {
        "M1": mt5.TIMEFRAME_M1,
        "M3": mt5.TIMEFRAME_M3,
        "M5": mt5.TIMEFRAME_M5,
        "M10": mt5.TIMEFRAME_M10,
        "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1
    }
    return timeframes.get(value, None)


# Tạo hàm để chuyển đổi từ khung thời gian MT5 sang số để lưu trữ
def convert_mt5_to_timeframe(value):
    mt5_timeframes = {
        mt5.TIMEFRAME_M1: "M1",
        mt5.TIMEFRAME_M3: "M3",
        mt5.TIMEFRAME_M5: "M5",
        mt5.TIMEFRAME_M10: "M10",
        mt5.TIMEFRAME_M15: "M15",
        mt5.TIMEFRAME_M20: "M20",
        mt5.TIMEFRAME_M30: "M30",
        mt5.TIMEFRAME_H1: "H1",
        mt5.TIMEFRAME_H4: "H4",
        mt5.TIMEFRAME_D1: "D1",
        mt5.TIMEFRAME_W1: "W1",
    }
    return mt5_timeframes.get(value, None)


# Đọc cấu hình từ file config.json
def load_config():
    with open('config\\files\\simple_ma_param.json', 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
        config.timeframe_short = convert_timeframe_to_mt5(config.timeframe_short)
        config.timeframe_long = convert_timeframe_to_mt5(config.timeframe_long)
        return config


# Lưu cấu hình vào file config.json
def save_config(config):
    with open('config\\files\\simple_ma_param.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)


def save_settings():
    config = {

    }
    save_config(config)
