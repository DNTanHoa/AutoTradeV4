import MetaTrader5 as mt5
from typing import List, Optional, Dict


def initialize_mt5_auth(login=None, password=None, server=None):
    """
    Initializes the MetaTrader 5 platform and logs in with the provided credentials.

    Args:
        login (int, optional): The account number to log in with.
        password (str, optional): The password for the account.
        server (str, optional): The server name for the account.

    Returns:
        bool: True if initialization and login are successful, False otherwise.
    """
    if not mt5.initialize():
        print("MT5 initialization failed")
        mt5.shutdown()
        return False

    if login and password and server:
        authorized = mt5.login(login=login, password=password, server=server)
        if not authorized:
            print("MT5 login failed")
            mt5.shutdown()
            return False

    return True


def place_order(symbol, volume, order_type, price=None, sl=None, tp=None, comment=None):
    order_type_dict = {
        'buy': mt5.ORDER_TYPE_BUY,
        'sell': mt5.ORDER_TYPE_SELL,
    }

    order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type_dict.get(order_type),
        "deviation": 20,
        "magic": 234000,
        'sl': sl,
        'tp': tp,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = mt5.order_send(order)

    if result is None:
        print(f"Order failed: result is None")
        mt5.shutdown()
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed, retcode: {result.retcode}")
        mt5.shutdown()
        return result

    print(f"Order placed successfully: {result}")
    return result


def close_position(symbol, ticket):
    # Attempt to close the position
    result = mt5.Close(symbol, ticket=ticket)

    if result:
        print(f"Position {ticket} closed successfully.")
        return {"success": True, "ticket": ticket, "error_code": None}
    else:
        error_code = mt5.last_error()
        print(f"Failed to close position {ticket}. Error code: {error_code}")
        return {"success": False, "ticket": ticket, "error_code": error_code}


def get_open_positions() -> Dict[str, Optional[List[mt5.Position]]]:
    positions = mt5.positions_get()

    if positions is None:
        error_code = mt5.last_error()
        print(f"Failed to get open positions. Error code: {error_code}")
        return {"success": False, "positions": [], "error_code": error_code}
    else:
        print(f"Retrieved {len(positions)} open positions.")
        return {"success": True, "positions": positions, "error_code": None}


def close_all_orders(order_type=None):
    # Retrieve open positions
    positions_info = get_open_positions()
    if not positions_info["success"]:
        return positions_info

    positions = positions_info["positions"]
    results = []

    for position in positions:
        if order_type is not None and position.type != order_type:
            continue
        result = close_position(position.symbol, position.ticket)
        results.append(result)

    return results


def close_all_buy_orders():
    print("Attempting to close all buy orders...")
    return close_all_orders(mt5.ORDER_TYPE_BUY)


def close_all_sell_orders():
    print("Attempting to close all sell orders...")
    return close_all_orders(mt5.ORDER_TYPE_SELL)


def close_all_profitable_orders():
    result = get_open_positions()
    if not result["success"]:
        print("No open positions to process.")
        return

    positions = result["positions"]

    for position in positions:
        profit = position.profit  # Ensure this attribute is recognized
        if profit > 0:
            close_position(position.symbol, position.ticket)


def update_order_sl_tp(position_id, new_sl=None, new_tp=None):
    # Initialize MetaTrader 5 connection
    if not mt5.initialize():
        print("Failed to initialize MetaTrader 5")
        return None

    # Get the position by ticket ID
    position = mt5.positions_get(ticket=position_id)
    if not position:
        print(f"No position found with ID {position_id}")
        mt5.shutdown()
        return None

    symbol = position[0].symbol

    # Create the request for updating SL/TP
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": position_id,
        "sl": new_sl,
        "tp": new_tp,
    }

    # Send the request
    result = mt5.order_send(request)

    # Check the result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to update SL/TP, retcode: {result.retcode} - {result.comment}")
        mt5.shutdown()
        return None

    print(f"SL/TP updated successfully for position ID {position_id}")
    mt5.shutdown()
    return result


def shutdown_mt5():
    mt5.shutdown()
