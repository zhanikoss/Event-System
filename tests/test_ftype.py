import pytest
from core.ftypes import Maybe, Either, Just, Nothing, Right, Left
from core.transforms import safe_ticket, validate_cart_item
from core.compose import create_order_pipeline
from core.domain import TicketType, CartItem, Quota, Rule, Price, Order

def test_maybe_monad_operations():
    """1. Тест основных операций Maybe монады"""
    # Test Just
    just_value = Maybe.just(10)
    assert just_value.map(lambda x: x * 2).get_or_else(0) == 20
    assert just_value.bind(lambda x: Maybe.just(x + 5)).get_or_else(0) == 15
    
    # Test Nothing
    nothing = Maybe.nothing()
    assert nothing.map(lambda x: x * 2).get_or_else(100) == 100
    assert nothing.bind(lambda x: Maybe.just(5)).get_or_else(50) == 50

def test_either_monad_operations():
    """2. Тест основных операций Either монады"""
    # Test Right
    right_value = Either.right("success")
    assert right_value.map(lambda x: x.upper()).get_or_else("fail") == "SUCCESS"
    assert right_value.bind(lambda x: Either.right(x + "!")).get_or_else("fail") == "success!"
    
    # Test Left
    left_value = Either.left("error")
    assert left_value.map(lambda x: x.upper()).get_or_else("default") == "default"
    assert left_value.bind(lambda x: Either.right("new")).get_or_else("fallback") == "fallback"

def test_safe_ticket_with_maybe():
    """3. Тест безопасного поиска билета с Maybe"""
    tickets = (
        TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP", refundable=True),
        TicketType(id="t2", event_id="e2", zone_id="z2", title="Standard", refundable=False),
    )
    
    # Найденный билет
    found = safe_ticket(tickets, "t1")
    assert found.get_or_else(None) is not None
    assert found.get_or_else(None).title == "VIP"
    
    # Не найденный билет
    not_found = safe_ticket(tickets, "t99")
    assert not_found.get_or_else("not_found") == "not_found"

def test_validate_cart_item_with_either():
    """4. Тест валидации корзины с Either"""
    item = CartItem(id="c1", ticket_type_id="t1", qty=3)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=2),)  # Доступно 8

    # Успешная валидация
    success_result = validate_cart_item(item, quotas, ())
    assert hasattr(success_result, 'value')
    assert success_result.value.qty == 3

    # Ошибка валидации (превышение лимита)
    rules = (
        Rule(
            id="r1",
            kind="per_user_limit",
            payload={"max_tickets": 2}
        ),
    )

    fail_result = validate_cart_item(item, quotas, rules)
    assert hasattr(fail_result, 'error')
    assert "limit" in fail_result.error["error"].lower()

def test_order_pipeline_composition():
    """5. Тест композиции пайплайна заказа"""
    cart_items = (CartItem(id="c1", ticket_type_id="t1", qty=2),)
    ticket_types = (TicketType(id="t1", event_id="e1", zone_id="z1", title="Test", refundable=True),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=5),)
    prices = (Price(id="p1", ticket_type_id="t1", amount=1500),)
    rules = ()
    
    # Успешный пайплайн
    result = create_order_pipeline(cart_items, ticket_types, quotas, rules, prices)
    assert hasattr(result, 'value')
    assert result.value.total == 3000  # 2 * 1500
    assert result.value.status == "held"
    
    # Пайплайн с ошибкой (пустая корзина)
    empty_result = create_order_pipeline((), ticket_types, quotas, rules, prices)
    assert hasattr(empty_result, 'error')  
    assert empty_result.error["error"] == "Cart is empty"