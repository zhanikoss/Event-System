import json
from functools import reduce
from core.domain import Venue, Hall, Event, Zone, TicketType, Price, CartItem, Order, Quota

def load_seed(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    venues = tuple(Venue(**v) for v in data["venues"])
    halls = tuple(Hall(**h) for h in data["halls"])
    events = tuple(Event(**e) for e in data["events"])
    zones = tuple(Zone(**z) for z in data["zones"])
    ticket_types = tuple(TicketType(**t) for t in data["ticket_types"])
    prices = tuple(Price(id=f"p{i+1}", **p) for i, p in enumerate(data["prices"]))
    
    quotas = tuple(Quota(**q) for q in data.get("quotas", []))
    
    orders_data = []
    for i, o in enumerate(data["orders"]):
        items = tuple(CartItem(id=f"ci{j+1}", **item) for j, item in enumerate(o["items"]))
        total = sum(next((p.amount for p in prices if p.ticket_type_id == item["ticket_type_id"]), 0) * item["qty"] 
                   for item in o["items"])
        orders_data.append(Order(
            id=o["id"],
            event_id=o.get("event_id", "e1"),
            items=items,
            total=total,
            status=o.get("status", "paid")
        ))
    orders = tuple(orders_data)
    
    return venues, halls, events, zones, ticket_types, prices, orders, quotas

def hold(cart: tuple[CartItem, ...], item: CartItem) -> tuple[CartItem, ...]:
    """Add item to cart"""
    return cart + (item,)

def release(cart: tuple[CartItem, ...], item_id: str) -> tuple[CartItem, ...]:
    """Remove item from cart by ID"""
    return tuple(item for item in cart if item.id != item_id)

def order_total(prices: tuple[Price, ...], items: tuple[CartItem, ...]) -> int:
    """Calculate total order amount (using reduce)"""
    return reduce(
        lambda acc, item: acc + next(
            p.amount for p in prices if p.ticket_type_id == item.ticket_type_id
        ) * item.qty,
        items,
        0
    )

def order_total_with_discount(prices: tuple[Price, ...], items: tuple[CartItem, ...], discount_ids: tuple[str, ...]) -> int:
    """Calculate total with 20% discount for specified tickets"""
    total = 0
    for item in items:
        price = next(p.amount for p in prices if p.ticket_type_id == item.ticket_type_id)
        if item.ticket_type_id in discount_ids:
            total += int(price * 0.8) * item.qty
        else:
            total += price * item.qty
    return total

def ticket_titles_upper(tickets: tuple[TicketType, ...]) -> list[str]:
    """Convert ticket titles to uppercase (using map)"""
    return list(map(lambda t: t.title.upper(), tickets))

def vip_tickets(tickets: tuple[TicketType, ...]) -> list[TicketType]:
    """Return only VIP tickets (using filter)"""
    return list(filter(lambda t: "VIP" in t.title.upper(), tickets))

def discounted_prices(prices: tuple[Price, ...]) -> list[int]:
    """Calculate 90% of original price (using map)"""
    return list(map(lambda p: int(p.amount * 0.9), prices))

def max_price(prices: tuple[Price, ...]) -> int:
    """Find maximum price (using max)"""
    return max(map(lambda p: p.amount, prices)) if prices else 0

def average_price(prices: tuple[Price, ...]) -> float:
    """Calculate average price"""
    return sum(map(lambda p: p.amount, prices)) / len(prices) if prices else 0

def available_quotas(quotas: tuple[Quota, ...]) -> list[dict]:
    """Find available quotas"""
    return [{"ticket_type_id": q.ticket_type_id, "available": q.total - q.sold} 
            for q in quotas if q.total > q.sold]