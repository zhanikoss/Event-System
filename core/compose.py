import time
from typing import Callable, Any, TypeVar, Tuple, Dict
from core.ftypes import Either
from core.domain import CartItem, Order, TicketType, Quota, Rule, Price

T = TypeVar('T')
U = TypeVar('U') 
V = TypeVar('V')

def compose(*funcs: Callable) -> Callable:
    """compose(f, g, h)(x) = f(g(h(x)))"""
    def composed(x):
        for f in reversed(funcs):
            x = f(x)
        return x
    return composed

def pipe(x: Any, *funcs: Callable) -> Any:
    """pipe(x, f, g, h) = h(g(f(x)))"""
    for f in funcs:
        x = f(x)
    return x

def create_order_pipeline(cart_items: Tuple[CartItem, ...], 
                         ticket_types: Tuple[TicketType, ...], 
                         quotas: Tuple[Quota, ...], 
                         rules: Tuple[Rule, ...],
                         prices: Tuple[Price, ...],
                         user_age: int = None) -> Either[Dict, Order]:
    """Order creation pipeline - ПРОСТАЯ РАБОЧАЯ ВЕРСИЯ БЕЗ COMPOSE"""
    
    # 1. Проверка пустой корзины
    if not cart_items:
        return Either.left({"error": "Cart is empty"})
    
    # 2. Проверка квот
    for item in cart_items:
        quota = next((q for q in quotas if q.ticket_type_id == item.ticket_type_id), None)
        if not quota or (quota.total - quota.sold) < item.qty:
            return Either.left({
                "error": f"Not enough tickets available",
                "available": quota.total - quota.sold if quota else 0,
                "requested": item.qty
            })
    
    # 3. Проверка возраста
    if user_age is not None and user_age < 18:
        return Either.left({
            "error": "Age restriction failed", 
            "message": "You must be at least 18 years old",
            "user_age": user_age,
            "required_age": 18
        })
    
    # 4. Расчет суммы
    total_amount = 0
    for item in cart_items:
        price = next((p.amount for p in prices if p.ticket_type_id == item.ticket_type_id), 0)
        total_amount += price * item.qty
    
    # 5. Создание заказа
    order = Order(
        id=f"order_{int(time.time())}",
        event_id=cart_items[0].ticket_type_id,
        items=cart_items,
        total=total_amount,
        status="paid"
    )
    
    return Either.right(order)