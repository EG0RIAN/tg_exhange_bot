from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime

@dataclass
class User:
    id: int
    tg_id: int
    first_name: Optional[str]
    username: Optional[str]
    lang: str = 'ru'
    is_blocked: bool = False
    created_at: Optional[datetime] = None

@dataclass
class Rate:
    id: int
    pair: str
    ask: float
    bid: float
    source: str
    updated_at: Optional[datetime]

@dataclass
class FAQ:
    id: int
    category: str
    question: str
    answer: str
    sort: int

@dataclass
class Order:
    id: int
    user_id: int
    pair: str
    amount: float
    payout_method: str
    contact: str
    status: str = 'new'
    rate_snapshot: Any = None
    created_at: Optional[datetime] = None

@dataclass
class LiveChat:
    user_id: int
    started_at: Optional[datetime]
    is_active: bool 