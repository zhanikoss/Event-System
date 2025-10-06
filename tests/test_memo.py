import pytest
import time
from core.memo import quote_tickets
from core.domain import Price, Quota, Rule

def test_quote_tickets_basic():
    """Тест базового квотирования"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=1000),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=5),)
    rules = ()
    
    total, available = quote_tickets("t1", 3, prices, quotas, rules)
    
    assert total == 3000  # 3 * 1000
    assert available == True  # 5 доступно (10-5), нужно 3

def test_quote_tickets_not_available():
    """Тест когда билетов недостаточно"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=1000),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=8),)
    rules = ()
    
    total, available = quote_tickets("t1", 5, prices, quotas, rules)
    
    assert available == False  # 2 доступно (10-8), нужно 5

def test_quote_tickets_caching():
    """Тест что кэширование работает"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=1000),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=5),)
    rules = ()
    
    # Первый вызов
    start_time = time.time()
    result1 = quote_tickets("t1", 2, prices, quotas, rules)
    time1 = time.time() - start_time
    
    # Второй вызов (должен быть быстрее из кэша)
    start_time = time.time()
    result2 = quote_tickets("t1", 2, prices, quotas, rules)
    time2 = time.time() - start_time
    
    assert result1 == result2
    assert time2 < time1  # Второй вызов должен быть быстрее

def test_quote_tickets_different_arguments():
    """Тест что разные аргументы дают разный результат"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=1000),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=5),)
    rules = ()
    
    result1 = quote_tickets("t1", 2, prices, quotas, rules)
    result2 = quote_tickets("t1", 3, prices, quotas, rules)
    
    assert result1 != result2  # Разное количество = разный результат

def test_quote_tickets_cache_info():
    """Тест статистики кэша"""
    prices = (Price(id="p1", ticket_type_id="t1", amount=1000),)
    quotas = (Quota(id="q1", ticket_type_id="t1", total=10, sold=5),)
    rules = ()
    
    # Очищаем кэш
    quote_tickets.cache_clear()
    
    # Делаем вызовы
    quote_tickets("t1", 2, prices, quotas, rules)
    quote_tickets("t1", 2, prices, quotas, rules)  # Должен попасть в кэш
    
    cache_info = quote_tickets.cache_info()
    assert cache_info.hits >= 1  # Должен быть как минимум 1 хит
    assert cache_info.misses >= 1  # И как минимум 1 промах