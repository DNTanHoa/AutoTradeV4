from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Signal(BaseModel):
    signal_key: str
    timestamp: datetime
    symbol: str
    signal: int  # e.g., "buy" or "sell"
    entry: float
    sl: float  # Stop Loss
    tp: float  # Take Profit
    limit_entry: Optional[int] = None
    buy_counter: Optional[int] = None
    sell_counter: Optional[int] = None
    lot_size: Optional[float] = None   # volume
    order_id: Optional[str] = None
    processed: bool = False
    note: Optional[str] = None
    first_shift: Optional[bool] = None
    first_shift_sl: Optional[float] = None
    first_shift_tp: Optional[float] = None
    second_shift: Optional[bool] = None
    second_shift_sl: Optional[float] = None
    second_shift_tp: Optional[float] = None
    third_shift: Optional[bool] = None
    third_shift_sl: Optional[float] = None
    third_shift_tp: Optional[float] = None
    fourth_shift: Optional[bool] = None
    fourth_shift_sl: Optional[float] = None
    fourth_shift_tp: Optional[float] = None
    fifth_shift: Optional[bool] = None
    fifth_shift_sl: Optional[float] = None
    fifth_shift_tp: Optional[float] = None
    sixth_shift: Optional[bool] = None
    sixth_shift_sl: Optional[float] = None
    sixth_shift_tp: Optional[float] = None
    seventh_shift: Optional[bool] = None
    seventh_shift_sl: Optional[float] = None
    seventh_shift_tp: Optional[float] = None
    eightth_shift: Optional[bool] = None
    eightth_shift_sl: Optional[float] = None
    eightth_shift_tp: Optional[float] = None
    nineth_shift: Optional[bool] = None
    nineth_shift_sl: Optional[float] = None
    nineth_shift_tp: Optional[float] = None
