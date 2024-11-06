from optparse import Option
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TradingStep(BaseModel):
    timestamp: datetime
    symbol: str
    capital: Optional[int] = None
    level: Optional[int] = None
    lot_size: Optional[float] = None
