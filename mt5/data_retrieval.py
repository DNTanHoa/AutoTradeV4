import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta


def initialize_mt5():
    if not mt5.initialize():
        print("MT5 initialization failed")
        mt5.shutdown()
        return False
    return True


def get_historical_data(symbol, timeframe, start, end):
    if not initialize_mt5():
        return None

    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None:
        print("No data retrieved")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


def get_account_info():
    # Khởi động MT5
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return None

    # Lấy thông tin tài khoản giao dịch
    account_info = mt5.account_info()
    if account_info is None:
        print("Failed to get account info")
        mt5.shutdown()
        return None

    # Chuyển đổi thông tin tài khoản thành từ điển để dễ dàng hiển thị
    account_info_dict = account_info.model_dump()

    # Đóng kết nối MT5
    mt5.shutdown()

    return account_info_dict


def get_history_orders(from_date, to_date):
    # Check if MetaTrader 5 is already initialized; if not, initialize it
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return None

    try:
        # Validate input types
        if not isinstance(from_date, datetime) or not isinstance(to_date, datetime):
            print("from_date and to_date must be datetime objects")
            return None

        # Fetch closed orders within the date range
        closed_orders = mt5.history_orders_get(from_date, to_date)

        # Check if any orders were returned
        if closed_orders is None:
            print(f"No closed orders found from {from_date} to {to_date}.")
            return None

        # Convert each order to a dictionary using attribute names
        closed_orders_list = [
            {
                "ticket": order.ticket,
                "time_setup": order.time_setup,
                "time_done": order.time_done,
                "symbol": order.symbol,
                "volume": order.volume,
                "price_open": order.price_open,
                "price_current": order.price_current,
                "type": order.type,
                "state": order.state,
                "comment": order.comment,
                # Add any other relevant fields here based on your needs
            }
            for order in closed_orders
        ]

        return closed_orders_list

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        # Always shut down the MT5 connection
        mt5.shutdown()


def check_position_exists(position_type: int) -> bool:
    """
    Kiểm tra xem có tồn tại vị thế cụ thể hay không.

    :param position_type: int - loại vị thế (mt5.ORDER_TYPE_BUY hoặc mt5.ORDER_TYPE_SELL)
    :return: bool - True nếu tồn tại vị thế với loại position_type, False nếu không có
    """

    # Lấy tất cả các vị thế hiện tại
    positions = mt5.positions_get()
    if positions is None:
        print("Không lấy được vị thế")
        return False  # Trả về False nếu không lấy được vị thế

    # Kiểm tra xem có vị thế cụ thể nào tồn tại không
    exists = any(pos.type == position_type for pos in positions)

    return exists  # Trả về kết quả là kiểu bool


def check_last_closed_position_type(days: int = 10) -> str:
    """
    Kiểm tra xem vị thế cuối cùng đã đóng là loại BUY hay SELL.

    :return: str - "buy" nếu vị thế cuối cùng là mua, "sell" nếu là bán, "none" nếu không có vị thế nào đã đóng
    """
    # Kết nối tới MetaTrader 5

    # Define the time range to retrieve recent deals (e.g., last 1 day)
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now() + timedelta(days=1)

    orders = mt5.history_orders_get(from_date, to_date)
    if orders is None or len(orders) == 0:
        print("No orders found in the specified time range, error:", mt5.last_error())
        return None

    # Convert deals to a list and sort by time to get the latest deal
    orders = list(orders)
    orders.sort(key=lambda order: order.time_setup, reverse=True)

    # Check the latest closed position
    for order in orders:
        if order.type == mt5.ORDER_TYPE_BUY:
            print("Last closed position was a SELL.")
            return "sell"  # Lệnh kết thúc là 1 lệnh buy thì trước đó là 1 vi thế sell
        elif order.type == mt5.ORDER_TYPE_SELL:
            print("Last closed position was a BUY.")
            return "buy"  # Lệnh kết thúc là 1 lệnh buy thì trước đó là 1 vi thế buy

    print("No closed positions found.")
    return "none"


def shutdown_mt5():
    mt5.shutdown()
