from core.ftypes import Maybe, Either, Right, Left
from core.domain import CartItem, Order, TicketType, Quota, Rule, Price
from typing import Tuple, Dict, Callable
from core.transforms import safe_ticket, validate_cart_item, validate_order

def create_order_pipeline(cart_items: Tuple[CartItem, ...],
                        ticket_types: Tuple[TicketType, ...],
                        quotas: Tuple[Quota, ...],
                        rules: Tuple[Rule, ...],
                        prices: Tuple[Price, ...]) -> Either[Dict, Order]:
    """Пайплайн создания заказа без try/except"""
    
    def calculate_total(valid_items: Tuple[CartItem, ...]) -> int:
        """Вычисление общей стоимости"""
        total = 0
        for item in valid_items:
            ticket = next((t for t in ticket_types if t.id == item.ticket_type_id), None)
            if ticket:
                price = next((p for p in prices if p.ticket_type_id == ticket.id), None)
                if price:
                    total += price.amount * item.qty
        return total
    
    # Валидируем все элементы корзины
    validated_items = []
    for item in cart_items:
        validation_result = validate_cart_item(item, quotas, rules)
        if hasattr(validation_result, 'error'):  # ← Left case
            return validation_result  # Возвращаем первую ошибку
        validated_items.append(validation_result.value)
    
    # ЕСЛИ КОРЗИНА ПУСТАЯ - возвращаем ошибку
    if not validated_items:
        return Either.left({"error": "Cart is empty"})  # ← ДОБАВЬ ЭТУ ПРОВЕРКУ!
    
    # Создаем заказ
    order = Order(
        id=f"order_{len(validated_items)}",
        event_id=validated_items[0].ticket_type_id,
        items=tuple(validated_items),
        total=calculate_total(tuple(validated_items)),
        status="held"
    )
    
    # Финальная валидация заказа
    return validate_order(order, rules)