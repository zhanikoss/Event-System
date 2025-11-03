from typing import Iterable, Iterator, Callable
from collections import deque
from datetime import datetime

def iter_orders(orders: tuple, predicate: Callable = None) -> Iterable:
    """
    Ленивый генератор заказов с фильтрацией
    
    Args:
        orders: Кортеж заказов для обработки
        predicate: Опциональная функция-фильтр
    
    Yields:
        Order: Заказы, удовлетворяющие условию фильтрации
    """
    for order in orders:
        if predicate is None or predicate(order):
            yield order

def lazy_gate_flow(scans: Iterable, window: int) -> Iterator[tuple[str, int]]:
    """
    Онлайн-подсчёт входов по воротам за скользящее окно минут
    
    Args:
        scans: Итератор сканирований
        window: Размер окна в минутах
    
    Yields:
        tuple[str, int]: Пары (gate_id, count) для каждого ворота
    """
    window_seconds = window * 60
    scans_in_window = deque()
    gate_counts = {}
    
    for scan in scans:
        current_time = datetime.fromisoformat(scan.ts)
        
        # Удаляем старые сканирования
        while scans_in_window:
            old_scan, old_time = scans_in_window[0]
            if (current_time - old_time).total_seconds() > window_seconds:
                scans_in_window.popleft()
                gate_counts[old_scan.gate_id] -= 1
                if gate_counts[old_scan.gate_id] == 0:
                    del gate_counts[old_scan.gate_id]
            else:
                break
        
        # Добавляем новое сканирование
        scans_in_window.append((scan, current_time))
        gate_counts[scan.gate_id] = gate_counts.get(scan.gate_id, 0) + 1
        
        # Возвращаем текущие счетчики
        for gate_id, count in gate_counts.items():
            yield (gate_id, count)

def simulate_scan_stream(count: int = 50):
    """Простой генератор сканирований для демо"""
    from datetime import datetime, timedelta
    import random
    
    # Английские названия ворот
    gate_ids = [
        "Main_Entrance",      # Главный вход
        "VIP_Entrance",       # VIP вход  
        "North_Gate",         # Северные ворота
        "Express_Entry",      # Экспресс вход
        "South_Entrance",     # Южный вход
        "West_Gate",          # Западные ворота
        "East_Access",        # Восточный доступ
        "Family_Entrance"     # Семейный вход
    ]
    base_time = datetime.now() - timedelta(minutes=30)
    
    class SimpleScan:
        def __init__(self, gate_id, ts):
            self.gate_id = gate_id
            self.ts = ts
    
    for i in range(count):
        scan_time = base_time + timedelta(minutes=i*0.5)
        yield SimpleScan(
            gate_id=random.choice(gate_ids),
            ts=scan_time.isoformat()
        )