import json
from core.ftypes import Maybe, Either
from functools import reduce
from core.domain import (
    User, Venue, Hall, Event, Zone, TicketType, 
    Price, CartItem, Order, Quota, AdmissionGate, 
    Scan, EventMsg, Rule
)
from typing import List, Tuple, Optional, Dict, Any

def load_seed(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Загружаем все сущности
    users = [User(**u) for u in data.get("users", [])]
    venues = [Venue(**v) for v in data.get("venues", [])]
    halls = tuple(Hall(**h) for h in data.get("halls", []))
    events = tuple(Event(**e) for e in data.get("events", []))
    zones = tuple(Zone(**z) for z in data.get("zones", []))
    ticket_types = tuple(TicketType(**t) for t in data.get("ticket_types", []))
    prices = tuple(Price(id=f"p{i+1}", **p) for i, p in enumerate(data.get("prices", [])))
    quotas = tuple(Quota(**q) for q in data.get("quotas", []))
    
    # Дополнительные сущности
    admission_gates = tuple(AdmissionGate(**g) for g in data.get("admission_gates", []))
    scans = tuple(Scan(**s) for s in data.get("scans", []))
    event_msgs = tuple(EventMsg(**m) for m in data.get("event_msgs", []))
    rules = tuple(Rule(**r) for r in data.get("rules", []))
    
    # Обработка заказов
    orders_data = []
    for i, o in enumerate(data.get("orders", [])):
        items = tuple(CartItem(id=f"ci{j+1}", **item) for j, item in enumerate(o["items"]))
        total = sum(
            next((p.amount for p in prices if p.ticket_type_id == item["ticket_type_id"]), 0) * item["qty"]
            for item in o["items"]
        )
        orders_data.append(Order(
            id=o["id"],
            event_id=o.get("event_id", "e1"),
            items=items,
            total=total,
            status=o.get("status", "paid")
        ))
    
    orders = tuple(orders_data)
    
    return (users, venues, halls, events, zones, ticket_types, 
            prices, orders, quotas, admission_gates, scans, event_msgs, rules)

# Существующие функции остаются без изменений
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
            (p.amount for p in prices if p.ticket_type_id == item.ticket_type_id),
            0
        ) * item.qty,
        items,
        0
    )

def get_ticket_display_name(ticket_type: TicketType, events: Tuple[Event, ...], zones: Tuple[Zone, ...]) -> str:
    """Получить красивое название билета"""
    event = next((e for e in events if e.id == ticket_type.event_id), None)
    zone = next((z for z in zones if z.id == ticket_type.zone_id), None)
    
    event_name = event.title if event else "Unknown Event"
    zone_name = zone.name if zone else "Unknown Zone"
    
    return f"{ticket_type.title} - {event_name} ({zone_name})"

def get_ticket_price(ticket_type_id: str, prices: Tuple[Price, ...]) -> int:
    """Получить цену билета"""
    price = next((p for p in prices if p.ticket_type_id == ticket_type_id), None)
    return price.amount if price else 0

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

def safe_ticket(ttypes: Tuple[TicketType, ...], tid: str) -> Maybe[TicketType]:
    """Безопасное получение типа билета"""
    ticket = next((t for t in ttypes if t.id == tid), None)
    return Maybe.just(ticket) if ticket else Maybe.nothing()

def validate_cart_item(item: CartItem, quotas: Tuple[Quota, ...],
                      rules: Tuple[Rule, ...]) -> Either[Dict, CartItem]:
    """Валидация элемента корзины"""
    # Проверяем квоты
    quota = next((q for q in quotas if q.ticket_type_id == item.ticket_type_id), None)
    if not quota:
        return Either.left({"error": "Quota not found", "item_id": item.id})

    if (quota.total - quota.sold) < item.qty:
        return Either.left({
            "error": "Not enough tickets",
            "available": quota.total - quota.sold,
            "requested": item.qty
        })

    # Проверяем правила (например, лимит на пользователя)
    user_limit_rules = [r for r in rules if r.kind == "per_user_limit"]
    for rule in user_limit_rules:
        payload_dict = rule.payload_dict  # ← ИСПРАВЬ ЗДЕСЬ! Используй payload_dict вместо payload
        max_tickets = payload_dict.get("max_tickets", 10)  # ← Теперь работает!
        if item.qty > max_tickets:
            return Either.left({
                "error": "User limit exceeded",
                "max_allowed": max_tickets,
                "requested": item.qty
            })
    
    return Either.right(item)

def validate_order(order: Order, rules: Tuple[Rule, ...], user_age: int = None) -> Either[Dict, Order]:
    """Валидация заказа с проверкой возраста"""
    age_rules = [r for r in rules if r.kind == "age_limit"]
    
    for rule in age_rules:
        payload_dict = rule.payload_dict
        min_age = payload_dict.get("min_age", 18)
        
        # Если возраст не передан, пропускаем проверку
        if user_age is None:
            continue
            
        # Проверяем возраст
        if user_age < min_age:
            return Either.left({
                "error": "Age restriction",
                "required_age": min_age,
                "user_age": user_age,
                "message": f"Minimum age {min_age}+ required. Your age: {user_age}"
            })
    
    return Either.right(order)
    # Проверка других правил может быть добавлена здесь
    # Например: даты мероприятия, доступность и т.д.
    
    return Either.right(order)  # Всегда возвращаем успех для демо

def validate_cart_item(item: CartItem, quotas: Tuple[Quota, ...],
                      rules: Tuple[Rule, ...]) -> Either[Dict, CartItem]:
    """Валидация элемента корзины"""
    # Проверяем квоты
    quota = next((q for q in quotas if q.ticket_type_id == item.ticket_type_id), None)
    if not quota:
        return Either.left({"error": "Quota not found", "item_id": item.id})

    if (quota.total - quota.sold) < item.qty:
        return Either.left({
            "error": "Not enough tickets",
            "available": quota.total - quota.sold,
            "requested": item.qty
        })

    # Проверяем правила (например, лимит на пользователя)
    user_limit_rules = [r for r in rules if r.kind == "per_user_limit"]
    for rule in user_limit_rules:
        payload_dict = rule.payload_dict  # ← ИСПРАВЬ ЗДЕСЬ! Используй payload_dict вместо payload
        max_tickets = payload_dict.get("max_tickets", 10)  # ← Теперь работает!
        if item.qty > max_tickets:
            return Either.left({
                "error": "User limit exceeded",
                "max_allowed": max_tickets,
                "requested": item.qty
            })
    
    return Either.right(item)