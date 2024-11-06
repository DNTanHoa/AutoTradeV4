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


def run_compound_backtest(df_signals, trailing_configs, init_capital, file_path, sheet_name):
    df_signals['PnL'] = 0.0
    df_signals['close_at'] = 0
    df_signals['lot_size'] = 0
    df_signals['lot_size'] = df_signals['lot_size'].astype(float)
    entry_price = 0
    current_capital = init_capital

    for i in range(1, len(df_signals)):
        sl_adjustments = [False] * len(trailing_configs)  # Tạo danh sách trạng thái cho các lần dời SL
        if df_signals['Signal'].iloc[i] == 1:  # Lệnh mua
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file(file_path, sheet_name, current_capital)
            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = (sl_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # Lệnh đạt TP
                        PnL = (tp_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Đóng và đảo lệnh
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = (sl_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        PnL = (df_signals['close'].iloc[j] - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
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

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file(file_path, sheet_name, current_capital)

            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:
                    if df_signals['low'].iloc[j] < tp_price:  # Lệnh đạt TP
                        PnL = (entry_price - tp_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = (entry_price - sl_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Đóng và đảo lệnh
                    if df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = (entry_price - sl_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        PnL = (entry_price - df_signals['close'].iloc[j]) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
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


def run_compound_backtest_with_entry_price(df_signals, trailing_configs, init_capital, file_path, sheet_name):
    df_signals['PnL'] = 0.0
    df_signals['close_at'] = 0
    df_signals['lot_size'] = 0
    df_signals['lot_size'] = df_signals['lot_size'].astype(float)
    entry_price = 0
    current_capital = init_capital

    for i in range(1, len(df_signals)):
        sl_adjustments = [False] * len(trailing_configs)  # Tạo danh sách trạng thái cho các lần dời SL
        if df_signals['Signal'].iloc[i] == 1:  # Lệnh mua
            entry_price = df_signals['entry_price'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file(file_path, sheet_name, current_capital)
            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = (sl_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # Lệnh đạt TP
                        PnL = (tp_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Đóng và đảo lệnh
                    if df_signals['low'].iloc[j] < sl_price:  # Lệnh bị quét SL
                        PnL = (sl_price - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        PnL = (df_signals['close'].iloc[j] - entry_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
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

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file(file_path, sheet_name, current_capital)

            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:
                    if df_signals['low'].iloc[j] < tp_price:  # Lệnh đạt TP
                        PnL = (entry_price - tp_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = (entry_price - sl_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Đóng và đảo lệnh
                    if df_signals['high'].iloc[j] > sl_price:  # Lệnh bị quét SL
                        PnL = (entry_price - sl_price) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        PnL = (entry_price - df_signals['close'].iloc[j]) * lot_size * 100
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'close_at'] = j
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


def run_compound_backtest_with_daily_target(df_signals, trailing_configs, init_capital, file_path, sheet_name,
                                            daily_price_diff_target):
    df_signals['PnL'] = 0.0
    df_signals['price_diff'] = 0.0
    df_signals['close_at'] = 0
    df_signals['lot_size'] = 0
    df_signals['lot_size'] = df_signals['lot_size'].astype(float)
    df_signals['date'] = df_signals['time'].dt.date  # Tạo cột date từ timestamp
    df_signals['daily_price_diff'] = 0.0  # Theo dõi tổng chênh lệch giá hàng ngày

    entry_price = 0
    current_capital = init_capital
    max_capital = 0
    daily_total_price_diff = 0.0  # Tổng chênh lệch giá trong ngày
    current_date = None
    level = 1
    up_level = False

    for i in range(1, len(df_signals)):
        current_row_date = df_signals['date'].iloc[i]

        # Reset lại chênh lệch giá khi ngày thay đổi
        if current_date != current_row_date:
            current_date = current_row_date
            up_level = False
            daily_total_price_diff = 0.0  # Reset chênh lệch giá mới cho ngày mới

        # Nếu tổng chênh lệch giá đã vượt quá mục tiêu ngày, bỏ qua các tín hiệu còn lại
        if daily_total_price_diff >= daily_price_diff_target:
            print(f"Đã đạt đủ {daily_total_price_diff} giá vàng trong ngày {current_row_date}. Bỏ qua tín hiệu.")
            if not up_level:
                level += 1
                up_level = True
            continue  # Bỏ qua các tín hiệu trong ngày hiện tại

        sl_adjustments = [False] * len(trailing_configs)  # Trạng thái điều chỉnh SL cho trailing stop loss

        if df_signals['Signal'].iloc[i] == 1:  # Tín hiệu mua (Buy signal)
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file_by_index(file_path, sheet_name, level)
            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != -1:  # Tín hiệu đóng (Close signal)
                    if df_signals['low'].iloc[j] < sl_price:  # SL hit
                        price_diff = sl_price - entry_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > tp_price:  # TP hit
                        price_diff = tp_price - entry_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == -1:  # Reverse signal
                    if df_signals['low'].iloc[j] < sl_price:  # SL hit
                        price_diff = sl_price - entry_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        price_diff = df_signals['close'].iloc[j] - entry_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    break

                # Điều chỉnh trailing stop loss
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] > entry_price + config.threshold and not sl_adjustments[idx]:
                        if sl_price < entry_price:
                            sl_price = entry_price + config.sl_adjustment
                        else:
                            sl_price = entry_price + config.sl_adjustment
                        tp_price += config.tp_adjustment
                        sl_adjustments[idx] = True

        elif df_signals['Signal'].iloc[i] == -1:  # Tín hiệu bán (Sell signal)
            entry_price = df_signals['close'].iloc[i]
            sl_price = df_signals['SL'].iloc[i]
            tp_price = df_signals['TP'].iloc[i]

            current_capital = init_capital + df_signals[(df_signals['close_at'] < i) & (df_signals['close_at'] > 0)][
                'PnL'].sum()
            lot_size = get_lot_size_from_file_by_index(file_path, sheet_name, level)
            df_signals.at[i, 'lot_size'] = lot_size

            for j in range(i + 1, len(df_signals)):
                if df_signals['Signal'].iloc[j] != 1:  # Tín hiệu đóng (Close signal)
                    if df_signals['low'].iloc[j] < tp_price:  # TP hit
                        price_diff = entry_price - tp_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                    elif df_signals['high'].iloc[j] > sl_price:  # SL hit
                        price_diff = entry_price - sl_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                        break
                elif df_signals['Signal'].iloc[j] == 1:  # Reverse signal
                    if df_signals['high'].iloc[j] > sl_price:  # SL hit
                        price_diff = entry_price - sl_price
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    else:
                        price_diff = entry_price - df_signals['close'].iloc[j]
                        PnL = price_diff * lot_size * 100  # Tính PnL
                        df_signals.at[df_signals.index[i], 'PnL'] = PnL
                        df_signals.at[df_signals.index[i], 'price_diff'] = price_diff
                        df_signals.at[df_signals.index[i], 'close_at'] = j
                    break

                # Điều chỉnh trailing stop loss cho lệnh bán (Sell orders)
                for idx, config in enumerate(trailing_configs):
                    if df_signals['close'].iloc[j] < entry_price - config.threshold and not sl_adjustments[idx]:
                        if sl_price > entry_price:
                            sl_price = entry_price - config.sl_adjustment
                        else:
                            sl_price = entry_price - config.sl_adjustment
                        tp_price -= config.tp_adjustment
                        sl_adjustments[idx] = True

        # Cập nhật tổng chênh lệch giá trong ngày và kiểm tra nếu đã đạt mục tiêu
        daily_total_price_diff += df_signals['price_diff'].iloc[i]
        df_signals.at[i, 'daily_price_diff'] = daily_total_price_diff

    # Tính tổng lợi nhuận
    df_signals['Cumulative_PnL'] = df_signals['PnL'].cumsum()
    # Xóa timezone nếu có
    df_signals['time'] = df_signals['time'].dt.tz_localize(None)

    # Xuất dữ liệu ra file Excel
    output_file = "trading_strategy_results_with_pnl_and_daily_price_diff_target.xlsx"
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_signals.to_excel(writer, sheet_name='Results')

    print(
        f"Dữ liệu đã được xuất ra file '{output_file}'. Tổng lợi nhuận: {df_signals['Cumulative_PnL'].iloc[-1]:.2f}. "
        f"Tổng số bậc đạt được: {level}")

    return df_signals


def get_lot_size_from_file(file_path, sheet_name, capital):
    # Đọc dữ liệu từ file Excel
    df_lot = pd.read_excel(file_path, sheet_name=sheet_name)
    # Tìm mức vốn phù hợp trong cột vốn và trả về lot size tương ứng
    matching_rows = df_lot[df_lot['Vốn'] <= capital]
    if not matching_rows.empty:
        return matching_rows['Lot Size'].iloc[-1]
    return df_lot['Lot Size'].iloc[0]  # Trường hợp không có vốn phù hợp


def get_lot_size_from_file_by_index(file_path, sheet_name, index):
    # Đọc dữ liệu từ file Excel
    df_lot = pd.read_excel(file_path, sheet_name=sheet_name)
    # Tìm mức vốn phù hợp trong cột vốn và trả về lot size tương ứng
    matching_rows = df_lot[df_lot['STT'] == index]
    if not matching_rows.empty:
        return matching_rows['Lot Size'].iloc[-1]
    return df_lot['Lot Size'].iloc[-1]
