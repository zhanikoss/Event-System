from core.domain import Zone
from typing import Tuple, Optional, List

def flatten_zone_tree(zones: Tuple[Zone, ...], root_id: Optional[str] = None) -> Tuple[Zone, ...]:
    """
    Рекурсивно разворачивает дерево зон в плоский список.
    """
    def _flatten_subtree(parent_id: Optional[str]) -> Tuple[Zone, ...]:
        result = []
        for zone in zones:
            if zone.parent_id == parent_id:
                result.append(zone)
                # Рекурсивно добавляем дочерние зоны
                result.extend(_flatten_subtree(zone.id))
        return tuple(result)
    
    if root_id is None:
        return zones
    
    return _flatten_subtree(root_id)

def expand_seatmap(zones: Tuple[Zone, ...], root_id: str) -> Tuple[Tuple[str, int], ...]:
    """
    Рекурсивно генерирует схему мест для иерархии зон.
    Возвращает кортеж кортежей (zone_id, seat_index).
    """
    def _expand_zone(zone_id: str, start_seat: int = 1) -> Tuple[Tuple[str, int], ...]:
        zone = next((z for z in zones if z.id == zone_id), None)
        if not zone:
            return ()
        
        result = []
        current_seat = start_seat
        
        # Если у зоны есть места, добавляем их
        if zone.seats is not None:
            for seat in range(1, zone.seats + 1):
                result.append((zone.id, current_seat))
                current_seat += 1
        
        # Рекурсивно обрабатываем дочерние зоны
        child_zones = [z for z in zones if z.parent_id == zone_id]
        for child in child_zones:
            child_result = _expand_zone(child.id, current_seat)
            result.extend(child_result)
            if child_result:
                current_seat = child_result[-1][1] + 1
        
        return tuple(result)
    
    return _expand_zone(root_id)

def get_zone_hierarchy(zones: Tuple[Zone, ...], zone_id: str, level: int = 0) -> List[Tuple[Zone, int]]:
    """
    Рекурсивно получает иерархию зон с отступами для отображения.
    Возвращает список (zone, level) для красивого отображения дерева.
    """
    result = []
    zone = next((z for z in zones if z.id == zone_id), None)
    if zone:
        result.append((zone, level))
        # Рекурсивно получаем дочерние зоны
        children = [z for z in zones if z.parent_id == zone_id]
        for child in children:
            result.extend(get_zone_hierarchy(zones, child.id, level + 1))
    return result

def calculate_total_seats(zones: Tuple[Zone, ...], root_id: str) -> int:
    """
    Рекурсивно вычисляет общее количество мест в иерархии зон.
    """
    def _count_seats(zone_id: str) -> int:
        zone = next((z for z in zones if z.id == zone_id), None)
        if not zone:
            return 0
        
        total = zone.seats if zone.seats else 0
        # Рекурсивно считаем места в дочерних зонах
        children = [z for z in zones if z.parent_id == zone_id]
        for child in children:
            total += _count_seats(child.id)
        
        return total
    
    return _count_seats(root_id)