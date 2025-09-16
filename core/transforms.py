import json
from functools import reduce
from .domain import Venue, Hall, Event, Zone, TicketType, Price, CartItem, Order

def load_seed(path: str) -> tuple[tuple[Venue, ...], tuple[Hall, ...], tuple[Event, ...], tuple[Zone, ...], tuple[TicketType, ...], tuple[Price, ...], tuple[Order, ...]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    venues = tuple(Venue(**v) for v in data["venues"])
    halls = tuple(Hall(**h) for h in data["halls"])
    events = tuple(Event(**e) for e in data["events"])
    zones = tuple(Zone(**z) for z in data["zones"])
    ticket_types = tuple(TicketType(**t) for t in data["ticket_types"])
    prices = tuple(Price(**p) for p in data["prices"])
    orders = tuple(Order(**o) for o in data["orders"])
    return venues, halls, events, zones, ticket_types, prices, orders

def hold(cart: tuple[CartItem, ...], it: CartItem) -> tuple[CartItem, ...]:
    return cart + (it,)

def release(cart: tuple[CartItem, ...], item_id: str) -> tuple[CartItem, ...]:
    return tuple(c for c in cart if c.ticket_type_id != item_id)

def order_total(prices: tuple[Price, ...], items: tuple[CartItem, ...]) -> int:
    return reduce(
        lambda acc, it: acc + next(p.amount for p in prices if p.ticket_type_id == it.ticket_type_id) * it.qty,
        items,
        0
    )

def order_total_with_discount(prices: tuple[Price, ...], items: tuple[CartItem, ...], discount_ids: tuple[str, ...]) -> int:
    def item_total(acc, it):
        price = next(p.amount for p in prices if p.ticket_type_id == it.ticket_type_id)
        if it.ticket_type_id in discount_ids:
            price = int(price * 0.8)  # скидка 20%
        return acc + price * it.qty
    return reduce(item_total, items, 0)

def ticket_titles_upper(tickets: tuple[TicketType, ...]) -> list[str]:
    return list(map(lambda t: t.title.upper(), tickets))

def vip_tickets(tickets: tuple[TicketType, ...]) -> list[TicketType]:
    return list(filter(lambda t: "VIP" in t.title.upper(), tickets))

def discounted_prices(prices: tuple[Price, ...]) -> list[int]:
    return [int(p.amount * 0.9) for p in prices]

def max_price(prices: tuple[Price, ...]) -> int:
    return reduce(lambda acc, p: acc if acc > p.amount else p.amount, prices, 0)
