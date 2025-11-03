import pytest
from core.lazy import iter_orders, lazy_gate_flow, simulate_scan_stream

def test_iter_orders_basic(sample_orders):
    """Тест 1: Базовая работа ленивого итератора"""
    result = list(iter_orders(sample_orders))
    assert len(result) == len(sample_orders)

def test_iter_orders_with_filter(sample_orders):
    """Тест 2: Фильтрация заказов по статусу"""
    paid_orders = list(iter_orders(sample_orders, lambda o: o.status == "paid"))
    assert all(order.status == "paid" for order in paid_orders)

def test_lazy_gate_flow_returns_tuples():
    """Тест 3: Проверка что функция возвращает кортежи"""
    scans = list(simulate_scan_stream(3))
    flow = lazy_gate_flow(scans, window=5)
    first_result = next(flow)
    assert isinstance(first_result, tuple) and len(first_result) == 2

def test_simulate_scan_stream_count():
    """Тест 4: Генерация правильного количества сканирований"""
    scans = list(simulate_scan_stream(10))
    assert len(scans) == 10

def test_empty_input():
    """Тест 5: Работа с пустыми данными"""
    empty_orders = list(iter_orders(()))
    empty_flow = list(lazy_gate_flow([], window=5))
    assert empty_orders == [] and empty_flow == []

@pytest.fixture
def sample_orders():
    """Фикстура с тестовыми заказами"""
    from core.domain import Order, CartItem
    return (
        Order("order_1", "event_1", (CartItem("item_1", "type_1", 2),), 1000, "paid"),
        Order("order_2", "event_1", (CartItem("item_2", "type_2", 1),), 500, "held"),
        Order("order_3", "event_2", (CartItem("item_3", "type_1", 1),), 600, "paid"),
    )