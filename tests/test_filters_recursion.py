import pytest
from core.filters import by_city, by_date_range, by_price_range
from core.recursion import flatten_zone_tree, calculate_total_seats
from core.domain import Event, Venue, Hall, TicketType, Price, Zone

def test_city_filter_with_real_cities():
    """Тест: фильтр по городу Almaty"""
    venues = (
        Venue(id="v1", name="Palace of Culture", city="Almaty"),
        Venue(id="v2", name="Open Air Arena", city="Astana"),
    )
    halls = (
        Hall(id="h1", venue_id="v1", name="Main Hall", capacity=1000),
        Hall(id="h3", venue_id="v2", name="Summer Stage", capacity=5000),
    )
    events = (
        Event(id="e1", hall_id="h1", title="Symphonic Concert", start="2024-01-15", end="2024-01-15"),
        Event(id="e3", hall_id="h3", title="Rock Festival", start="2024-02-01", end="2024-02-03"),
    )
    
    result = by_city("Almaty")(events, venues, halls)
    assert len(result) == 1
    assert result[0].title == "Symphonic Concert"

def test_price_filter_with_real_prices():
    """Тест: фильтр по цене 5000-15000 ₸"""
    tickets = (
        TicketType(id="t1", event_id="e1", zone_id="z1", title="VIP Concert", refundable=True),
        TicketType(id="t2", event_id="e1", zone_id="z2", title="Standard Concert", refundable=True),
        TicketType(id="t3", event_id="e1", zone_id="z3", title="Student Concert", refundable=False),
    )
    prices = (
        Price(id="p1", ticket_type_id="t1", amount=15000),
        Price(id="p2", ticket_type_id="t2", amount=8000),
        Price(id="p3", ticket_type_id="t3", amount=4000),
    )
    
    result = by_price_range(5000, 15000)(tickets, prices)
    assert len(result) == 2  # VIP (15000) и Standard (8000)
    ticket_titles = [t.title for t in result]
    assert "VIP Concert" in ticket_titles
    assert "Standard Concert" in ticket_titles

def test_date_filter_with_real_dates():
    """Тест: фильтр по дате января 2024"""
    events = (
        Event(id="e1", hall_id="h1", title="Symphonic Concert", start="2024-01-15", end="2024-01-15"),
        Event(id="e2", hall_id="h2", title="Jazz Evening", start="2024-01-20", end="2024-01-20"),
        Event(id="e3", hall_id="h3", title="Rock Festival", start="2024-02-01", end="2024-02-03"),
    )
    
    result = by_date_range("2024-01-01", "2024-01-31")(events)
    assert len(result) == 2  # Только январские события
    event_titles = [e.title for e in result]
    assert "Symphonic Concert" in event_titles
    assert "Jazz Evening" in event_titles

def test_recursion_calculate_seats_hierarchy():
    """Тест: рекурсивный подсчёт мест в иерархии"""
    zones = (
        Zone(id="main", hall_id="h1", name="Main", parent_id=None, seats=100),
        Zone(id="vip", hall_id="h1", name="VIP", parent_id="main", seats=20),
        Zone(id="balcony", hall_id="h1", name="Balcony", parent_id="main", seats=30),
    )
    
    total_seats = calculate_total_seats(zones, "main")
    assert total_seats == 150  # 100 + 20 + 30

def test_recursion_calculate_real_seats():
    """Тест: подсчёт мест для реальных зон"""
    zones = (
        Zone(id="z1", hall_id="h1", name="Parterre", parent_id=None, seats=500),
        Zone(id="z2", hall_id="h1", name="Balcony", parent_id=None, seats=300),
    )
    
    # Считаем места для каждой зоны отдельно (у них нет иерархии)
    seats1 = calculate_total_seats(zones, "z1")
    seats2 = calculate_total_seats(zones, "z2")
    
    assert seats1 == 500
    assert seats2 == 300