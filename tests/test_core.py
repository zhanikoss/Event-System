import pytest
from core.domain import Price, TicketType, CartItem, Quota
from core.transforms import (
    order_total, ticket_titles_upper, vip_tickets, 
    discounted_prices, max_price
)

def test_order_total():
    """Считает общую сумму заказа"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=100),)
    cart = (CartItem(id="c1", ticket_type_id="t1", qty=2),)
    assert order_total(prices, cart) == 200  # 100 * 2 = 200

def test_ticket_titles_upper():
    """Переводит названия билетов в верхний регистр"""
    tickets = (
        TicketType(id="t1", event_id="e1", zone_id="z1", title="vip ticket", refundable=True),
        TicketType(id="t2", event_id="e1", zone_id="z2", title="standard ticket", refundable=False)
    )
    result = ticket_titles_upper(tickets)
    assert result == ["VIP TICKET", "STANDARD TICKET"]

def test_vip_tickets_filter():
    """Находит только VIP билеты"""
    tickets = (
        TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP Ticket", refundable=True),
        TicketType(id="t2", event_id="e1", zone_id="z2", title="Standard Ticket", refundable=False)
    )
    result = vip_tickets(tickets)
    assert len(result) == 1
    assert result[0].title == "VIP Ticket"

def test_discounted_prices():
    """Считает цены со скидкой 10%"""
    prices = (
        Price(id="p1", ticket_type_id="t1", amount=100),
        Price(id="p2", ticket_type_id="t2", amount=50)
    )
    result = discounted_prices(prices)
    assert result == [90, 45]  # 100-10%=90, 50-10%=45

def test_max_price():
    """Находит максимальную цену"""
    prices = (
        Price(id="p1", ticket_type_id="t1", amount=100),
        Price(id="p2", ticket_type_id="t2", amount=200),
        Price(id="p3", ticket_type_id="t3", amount=50)
    )
    assert max_price(prices) == 200