import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.service import CatalogService, TicketService, FlowService, ReportService, compose, pipe
from core.domain import TicketType, Order, CartItem, Scan, Venue, Hall, Event, Price, Quota
from core.ftypes import Either


class TestComposition:
    """Тест 1: Утилиты композиции"""
    
    def test_compose_and_pipe(self):
        def double(x): return x * 2
        def add_five(x): return x + 5
        def square(x): return x * x
        
        # compose(f, g, h)(x) = f(g(h(x)))
        composed = compose(square, add_five, double)
        result1 = composed(3)  # square(add_five(double(3))) = square(add_five(6)) = square(11) = 121
        
        # pipe(x, f, g, h) = h(g(f(x)))
        result2 = pipe(3, double, add_five, square)  # square(add_five(double(3))) = 121
        
        assert result1 == 121
        assert result2 == 121


class TestCatalogService:
    """Тест 2: Поиск в каталоге"""
    
    def test_search_filters(self):
        venues = (Venue(id="v1", name="Arena", city="Almaty"),)
        halls = (Hall(id="h1", venue_id="v1", name="Main", capacity=1000),)
        events = (Event(id="e1", hall_id="h1", title="Concert", start="2025-01-01", end="2025-01-01"),)
        ticket_types = (
            TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP", refundable=True),
            TicketType(id="t2", event_id="e1", zone_id="z2", title="Standard", refundable=False),
        )
        prices = (Price(id="p1", ticket_type_id="t1", amount=10000), Price(id="p2", ticket_type_id="t2", amount=5000))
        quotas = (Quota(id="q1", ticket_type_id="t1", total=100, sold=50), Quota(id="q2", ticket_type_id="t2", total=200, sold=150))
        
        service = CatalogService(filters={})
        result = service.search(
            req={"city": "Almaty", "price_range": (8000, 12000)},
            ticket_types=ticket_types,
            events=events,
            venues=venues,
            halls=halls,
            prices=prices,
            quotas=quotas
        )
        
        # Должен найти только VIP билет (цена 10000 в диапазоне 8000-12000)
        assert len(result) == 1
        assert "t1" in result


class TestTicketService:
    """Тест 3: Подтверждение заказа"""
    
    def test_order_confirmation_success(self):
        cart_items = (CartItem(id="c1", ticket_type_id="t1", qty=2),)
        ticket_types = (TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP", refundable=True),)
        events = (Event(id="e1", hall_id="h1", title="Concert", start="2025-01-01", end="2025-01-01"),)
        prices = (Price(id="p1", ticket_type_id="t1", amount=10000),)
        quotas = (Quota(id="q1", ticket_type_id="t1", total=100, sold=50),)
        
        order = Order(id="test", event_id="e1", items=cart_items, total=20000, status="pending")
        
        service = TicketService(quoter=lambda x: x, validators=(), finalizer=lambda x: x)
        result = service.confirm(order, quotas, ticket_types, events, prices, user_age=25)
        
        assert hasattr(result, 'value')  # Успешный результат
        assert result.value.status == "paid"


class TestFlowService:
    """Тест 4: Аналитика потоков"""
    
    def test_gate_analytics(self):
        scans = (
            Scan(id="s1", gate_id="gate1", order_id="o1", ok=True, ts="2025-01-01T10:00:00"),
            Scan(id="s2", gate_id="gate1", order_id="o2", ok=False, ts="2025-01-01T10:05:00"),
            Scan(id="s3", gate_id="gate1", order_id="o3", ok=True, ts="2025-01-01T10:10:00"),
        )
        
        service = FlowService(aggregators={})
        result = service.gate_snapshot("gate1", "2025-01-01T10:15:00", scans)
        
        assert result["gate_id"] == "gate1"
        assert result["total_scans"] == 3
        assert result["successful_scans"] == 2
        assert result["success_rate"] == pytest.approx(66.67, 0.01)


class TestReportService:
    """Тест 5: Генерация отчетов"""
    
    def test_daily_sales_report(self):
        cart_items = (CartItem(id="c1", ticket_type_id="t1", qty=2),)
        orders = (
            Order(id="o1", event_id="e1", items=cart_items, total=20000, status="paid"),
            Order(id="o2", event_id="e1", items=cart_items, total=20000, status="paid"),
        )
        ticket_types = (TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP", refundable=True),)
        
        service = ReportService(aggregators={})
        result = service.daily_report("2025-01-01", orders, ticket_types)
        
        assert result["date"] == "2025-01-01"
        assert result["total_revenue"] == 40000
        assert result["total_tickets_sold"] == 4
        assert result["ticket_type_breakdown"]["VIP"] == 4