from typing import Tuple, Callable, Any
from core.domain import Event, Venue, Hall, TicketType, Price, Zone
from functools import reduce

def by_city(city: str) -> Callable:
    def filter_func(data: Tuple[Event, ...], venues: Tuple[Venue, ...], halls: Tuple[Hall, ...]) -> Tuple[Event, ...]:
        city_venues = tuple(filter(lambda v: v.city.lower() == city.lower(), venues))
        venue_ids = set(map(lambda v: v.id, city_venues))
        city_halls = tuple(filter(lambda h: h.venue_id in venue_ids, halls))
        hall_ids = set(map(lambda h: h.id, city_halls))
        return tuple(filter(lambda e: e.hall_id in hall_ids, data))
    return filter_func

def by_date_range(start: str, end: str) -> Callable:
    def filter_func(events: Tuple[Event, ...]) -> Tuple[Event, ...]:
        return tuple(filter(lambda e: start <= e.start <= end, events))
    return filter_func

def by_price_range(lo: int, hi: int) -> Callable:
    def filter_func(ticket_types: Tuple[TicketType, ...], prices: Tuple[Price, ...]) -> Tuple[TicketType, ...]:
        price_dict = dict(map(lambda p: (p.ticket_type_id, p.amount), prices))
        return tuple(filter(lambda t: lo <= price_dict.get(t.id, 0) <= hi, ticket_types))
    return filter_func

def by_zone_name(substr: str) -> Callable:
    def filter_func(zones: Tuple[Zone, ...]) -> Tuple[Zone, ...]:
        return tuple(filter(lambda z: substr.lower() in z.name.lower(), zones))
    return filter_func

def compose_filters(*filters: Callable) -> Callable:
    def composed(*args, **kwargs):
        if not filters:
            return args[0] if args else None
            
        result = filters[0](*args, **kwargs)
        for filter_func in filters[1:]:
            try:
                result = filter_func(result)
            except TypeError:
                result = filter_func(result, *args[1:], **kwargs)
        return result
    return composed