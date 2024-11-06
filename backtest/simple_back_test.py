import numpy as np
import pandas as pd


def calculate_sl_tp(df_signals, min_sl, min_tp, lot_standard):
    df_signals['close'] = df_signals['close_short']
    df_signals['high'] = df_signals['high_short']
    df_signals['low'] = df_signals['low_short']
    df_signals['open'] = df_signals['open_short']
    df_signals['MA'] = df_signals['MA_short']
    df_signals['SL'] = np.where(df_signals['Signal'] == 1, df_signals['close'] - min_sl * lot_standard,
                                np.where(df_signals['Signal'] == -1, df_signals['close'] + min_sl * lot_standard,
                                         np.nan))
    df_signals['TP'] = np.where(df_signals['Signal'] == 1, df_signals['close'] + min_tp * lot_standard,
                                np.where(df_signals['Signal'] == -1, df_signals['close'] - min_tp * lot_standard,
                                         np.nan))

    return df_signals


def calculate_sl_tp_with_entry_price(df_signals, min_sl, min_tp, lot_standard):
    df_signals['close'] = df_signals['close_short']
    df_signals['high'] = df_signals['high_short']
    df_signals['low'] = df_signals['low_short']
    df_signals['open'] = df_signals['open_short']
    df_signals['MA'] = df_signals['MA_short']
    df_signals['SL'] = np.where(df_signals['Signal'] == 1, df_signals['entry_price'] - min_sl * lot_standard,
                                np.where(df_signals['Signal'] == -1, df_signals['entry_price'] + min_sl * lot_standard,
                                         np.nan))
    df_signals['TP'] = np.where(df_signals['Signal'] == 1, df_signals['entry_price'] + min_tp * lot_standard,
                                np.where(df_signals['Signal'] == -1, df_signals['entry_price'] - min_tp * lot_standard,
                                         np.nan))

    return df_signals


def run_simple_backtest(df_signals, trailing_configs):
    df_signals['PnL'] = 0.0
    entry_price = 0

    for i in range(1, len(df_signals)):
        sl_adjustments = [False] * len(trailing_configs)  # Tạo danh sách trạng thái cho các lần dời SL
        if df_signals['Signal'].iloc[i] == 1:  # Lệnh mua
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # Lệnh đạt TP
                        PnL = tp_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Đóng và đảo lệnh
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = df_signals['close'].iloc[j] - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    break

                # Dời SL/TP dựa trên các cấu hình dời
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] > entry_price + config.threshold and not sl_adjustments[idx]:
                        if sl_price < entry_price:
                            sl_price = entry_price + config.sl_adjustment
                        else:
                            sl_price = entry_price + config.sl_adjustment
                        tp_price += config.tp_adjustment
                        sl_adjustments[idx] = True

        elif df_signals['Signal'].iloc[i] == -1:  # Lệnh bán
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:
                    if df_signals['low'].iloc[j] < tp_price:  # Lệnh đạt TP
                        PnL = entry_price - tp_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Đóng và đảo lệnh
                    if df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = entry_price - df_signals['close'].iloc[j]
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    break

                # Dời SL/TP cho lệnh bán
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] < entry_price - config.threshold and not sl_adjustments[idx]:
                        if sl_price > entry_price:
                            sl_price = entry_price - config.sl_adjustment
                        else:
                            sl_price = entry_price - config.sl_adjustment
                        tp_price -= config.tp_adjustment
                        sl_adjustments[idx] = True

    # Tính tổng lợi nhuận
    df_signals['Cumulative_PnL'] = df_signals['PnL'].cumsum()
    # Loại bỏ thông tin múi giờ (timezone unaware)
    df_signals['time'] = df_signals['time'].dt.tz_localize(None)

    # Xuất dữ liệu ra file Excel
    output_file = "trading_strategy_results.xlsx"
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_signals.to_excel(writer, sheet_name='Results')

    print(f"Dữ liệu đã được xuất ra file '{output_file}'. Tổng lợi nhuận: {df_signals['Cumulative_PnL'].iloc[-1]:.2f}")

    return df_signals


def run_simple_backtest_with_entry_price(df_signals, trailing_configs):
    df_signals['PnL'] = 0.0
    entry_price = 0

    for i in range(1, len(df_signals)):
        sl_adjustments = [False] * len(trailing_configs)  # Tạo danh sách trạng thái cho các lần dời SL
        if df_signals['Signal'].iloc[i] == 1:  # Lệnh mua
            entry_price = df_signals['entry_price'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # Lệnh đạt TP
                        PnL = tp_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Đóng và đảo lệnh
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = df_signals['close'].iloc[j] - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    break

                # Dời SL/TP dựa trên các cấu hình dời
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] > entry_price + config.threshold and not sl_adjustments[idx]:
                        if sl_price < entry_price:
                            sl_price = entry_price + config.sl_adjustment
                        else:
                            sl_price = entry_price + config.sl_adjustment
                        tp_price += config.tp_adjustment
                        sl_adjustments[idx] = True

        elif df_signals['Signal'].iloc[i] == -1:  # Lệnh bán
            entry_price = df_signals['entry_price'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:
                    if df_signals['low'].iloc[j] < tp_price:  # Lệnh đạt TP
                        PnL = entry_price - tp_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Đóng và đảo lệnh
                    if df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = entry_price - df_signals['close'].iloc[j]
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    break

                # Dời SL/TP cho lệnh bán
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] < entry_price - config.threshold and not sl_adjustments[idx]:
                        if sl_price > entry_price:
                            sl_price = entry_price - config.sl_adjustment
                        else:
                            sl_price = entry_price - config.sl_adjustment
                        tp_price -= config.tp_adjustment
                        sl_adjustments[idx] = True

    # Tính tổng lợi nhuận
    df_signals['Cumulative_PnL'] = df_signals['PnL'].cumsum()
    # Loại bỏ thông tin múi giờ (timezone unaware)
    df_signals['time'] = df_signals['time'].dt.tz_localize(None)

    # Xuất dữ liệu ra file Excel
    output_file = "trading_strategy_results.xlsx"
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_signals.to_excel(writer, sheet_name='Results')

    print(f"Dữ liệu đã được xuất ra file '{output_file}'. Tổng lợi nhuận: {df_signals['Cumulative_PnL'].iloc[-1]:.2f}")

    return df_signals


def run_simple_backtest_with_daily_target(df_signals, trailing_configs, daily_target_profit):
    df_signals['PnL'] = 0.0
    df_signals['Cumulative_PnL'] = 0.0
    entry_price = 0
    current_day = None
    daily_pnl = 0.0  # Lợi nhuận tích lũy trong ngày

    for i in range(1, len(df_signals)):
        df_signals['date'] = pd.to_datetime(df_signals['time'])
        sl_adjustments = [False] * len(trailing_configs)  # Tạo danh sách trạng thái cho các lần dời SL
        current_signal_day = df_signals['date'].iloc[i].date()  # Giả sử cột 'date' chứa thông tin ngày
        # Kiểm tra nếu ngày đã thay đổi, reset lợi nhuận hàng ngày
        if current_signal_day != current_day:
            current_day = current_signal_day
            daily_pnl = 0.0

        # Nếu đã đạt được lợi nhuận hàng ngày, bỏ qua các tín hiệu khác
        if daily_pnl >= daily_target_profit:
            print(f"Đã đạt đủ {daily_target_profit} giá vàng trong ngày {current_signal_day}. Bỏ qua tín hiệu.")
            continue

        if df_signals['Signal'].iloc[i] == 1:  # Lệnh mua
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # Lệnh đạt TP
                        PnL = tp_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Đóng và đảo lệnh
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = sl_price - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = df_signals['close'].iloc[j] - entry_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                    break

                # Dời SL/TP dựa trên các cấu hình dời
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] > entry_price + config.threshold and not sl_adjustments[idx]:
                        if sl_price < entry_price:
                            sl_price = entry_price + config.sl_adjustment
                        else:
                            sl_price = entry_price + config.sl_adjustment
                        tp_price += config.tp_adjustment
                        sl_adjustments[idx] = True

        elif df_signals['Signal'].iloc[i] == -1:  # Lệnh bán
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:
                    if df_signals['low'].iloc[j] < tp_price:  # Lệnh đạt TP
                        PnL = entry_price - tp_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Đóng và đảo lệnh
                    if df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = entry_price - sl_price
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    else:
                        PnL = entry_price - df_signals['close'].iloc[j]
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                    daily_pnl += PnL  # Cộng vào lợi nhuận hàng ngày
                    break

                # Dời SL/TP cho lệnh bán
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] < entry_price - config.threshold and not sl_adjustments[idx]:
                        if sl_price > entry_price:
                            sl_price = entry_price - config.sl_adjustment
                        else:
                            sl_price = entry_price - config.sl_adjustment
                        tp_price -= config.tp_adjustment
                        sl_adjustments[idx] = True

        # Cập nhật lợi nhuận tích lũy
        df_signals['Cumulative_PnL'] = df_signals['PnL'].cumsum()

    # Loại bỏ thông tin múi giờ (timezone unaware)
    df_signals['time'] = df_signals['time'].dt.tz_localize(None)
    df_signals['date'] = df_signals['date'].dt.tz_localize(None)
    # Xuất dữ liệu ra file Excel
    output_file = "trading_strategy_results.xlsx"
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_signals.to_excel(writer, sheet_name='Results')

    print(f"Dữ liệu đã được xuất ra file '{output_file}'. Tổng lợi nhuận: {df_signals['Cumulative_PnL'].iloc[-1]:.2f}")

    return df_signals


def calculate_strategy_summary(df_signals):
    result = {}
    total_profit_order = (df_signals['PnL'] > 0).sum()
    total_loss_order = (df_signals['PnL'] < 0).sum()
    pnl_rate = total_profit_order / total_loss_order

    result = {
        "total_profit_order": total_profit_order,
        "total_loss_order": total_loss_order,
        "pnl_rate": pnl_rate
    }
    return result