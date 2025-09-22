from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Venue:
    id: str
    name: str
    city: str


@dataclass(frozen=True)
class Hall:
    id: str
    venue_id: str
    name: str
    capacity: int


@dataclass(frozen=True)
class Zone:
    id: str
    hall_id: str
    name: str
    parent_id: Optional[str] = None
    seats: Optional[int] = None


@dataclass(frozen=True)
class Event:
    id: str
    hall_id: str
    title: str
    start: str
    end: str


@dataclass(frozen=True)
class TicketType:
    id: str
    event_id: str
    zone_id: str
    title: str
    refundable: bool


@dataclass(frozen=True)
class Price:
    id: str
    ticket_type_id: str
    amount: int
    currency: str = "KZT"


@dataclass(frozen=True)
class Quota:
    id: str
    ticket_type_id: str
    total: int
    sold: int


@dataclass(frozen=True)
class CartItem:
    id: str
    ticket_type_id: str
    qty: int


@dataclass(frozen=True)
class Order:
    id: str
    event_id: str
    items: Tuple[CartItem, ...]
    total: int
    status: str  # held/paid/cancelled


@dataclass(frozen=True)
class AdmissionGate:
    id: str
    hall_id: str
    name: str


@dataclass(frozen=True)
class Scan:
    id: str
    order_id: str
    gate_id: str
    ts: str
    ok: bool


@dataclass(frozen=True)
class EventMsg:
    id: str
    ts: str
    name: str
    payload: dict


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    payload: dict