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
    
    # Обрабатываем квоты если они есть
    quotas = tuple(Quota(**q) for q in data.get("quotas", []))
    
    # Обрабатываем заказы
    orders_data = []
    for i, o in enumerate(data["orders"]):
        items = tuple(CartItem(id=f"ci{j+1}", **item) for j, item in enumerate(o["items"]))
        # Временно считаем total
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
    """Добавляет товар в корзину"""
    return cart + (item,)


def release(cart: tuple[CartItem, ...], item_id: str) -> tuple[CartItem, ...]:
    """Удаляет товар из корзины по ID"""
    return tuple(item for item in cart if item.id != item_id)


def order_total(prices: tuple[Price, ...], items: tuple[CartItem, ...]) -> int:
    """Считает общую сумму заказа"""
    return reduce(
        lambda acc, item: acc + next(
            p.amount for p in prices if p.ticket_type_id == item.ticket_type_id
        ) * item.qty,
        items,
        0
    )


def order_total_with_discount(prices: tuple[Price, ...], items: tuple[CartItem, ...], discount_ids: tuple[str, ...]) -> int:
    """Считает сумму со скидкой 20% для указанных ticket_type_id"""
    total = 0
    for item in items:
        price = next(p.amount for p in prices if p.ticket_type_id == item.ticket_type_id)
        if item.ticket_type_id in discount_ids:
            total += int(price * 0.8) * item.qty
        else:
            total += price * item.qty
    return total


def ticket_titles_upper(tickets: tuple[TicketType, ...]) -> list[str]:
    """Переводит названия билетов в верхний регистр"""
    return [ticket.title.upper() for ticket in tickets]


def vip_tickets(tickets: tuple[TicketType, ...]) -> list[TicketType]:
    """Возвращает только VIP билеты"""
    return [ticket for ticket in tickets if "VIP" in ticket.title.upper()]


def discounted_prices(prices: tuple[Price, ...]) -> list[int]:
    """Считает 90% от оригинальной цены"""
    return [int(price.amount * 0.9) for price in prices]


def max_price(prices: tuple[Price, ...]) -> int:
    """Находит максимальную цену"""
    return max(price.amount for price in prices) if prices else 0


def average_price(prices: tuple[Price, ...]) -> float:
    """Средняя цена"""
    return sum(p.amount for p in prices) / len(prices) if prices else 0


def available_quotas(quotas: tuple[Quota, ...]) -> list[dict]:
    """Доступные квоты"""
    return [{"ticket_type_id": q.ticket_type_id, "available": q.total - q.sold} 
            for q in quotas if q.total > q.sold]