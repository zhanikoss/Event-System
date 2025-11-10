from typing import Dict, Any
from datetime import datetime
from core.frp import EventMsg, event_bus

def hold_analytics_handler(event: EventMsg, state: Dict) -> Dict:
    """Аналитика холдов"""
    if event.name == "HOLD":
        return {
            "type": "hold_analytics",
            "active_holds": state["stats"]["active_holds"],
            "total_holds": len([e for e in state["events"] if e.name == "HOLD"])
        }
    return {}

def sales_analytics_handler(event: EventMsg, state: Dict) -> Dict:
    """Аналитика продаж по часам"""
    if event.name == "PURCHASED":
        purchases = [e for e in state["events"] if e.name == "PURCHASED"]
        hourly_sales = {}
        
        for purchase in purchases:
            hour = datetime.fromisoformat(purchase.ts).strftime("%H:00")
            hourly_sales[hour] = hourly_sales.get(hour, 0) + 1
        
        return {
            "type": "sales_analytics", 
            "hourly_sales": hourly_sales,
            "total_revenue": state["stats"]["total_revenue"]
        }
    return {}

def gate_analytics_handler(event: EventMsg, state: Dict) -> Dict:
    """Аналитика ворот в реальном времени"""
    if event.name == "SCANNED":
        scans = [e for e in state["events"] if e.name == "SCANNED"][-50:]
        
        gate_stats = {}
        for scan in scans:
            gate_id = scan.payload.get("gate_id", "unknown")
            if gate_id not in gate_stats:
                gate_stats[gate_id] = {"total": 0, "successful": 0}
            
            gate_stats[gate_id]["total"] += 1
            if scan.payload.get("ok", False):
                gate_stats[gate_id]["successful"] += 1
        
        success_rate = state["stats"]["successful_scans"] / max(state["stats"]["total_scans"], 1)
        
        return {
            "type": "gate_analytics",
            "gate_stats": gate_stats,
            "success_rate": success_rate
        }
    return {}
def search_analytics_handler(event: EventMsg, state: Dict) -> Dict:
    """Аналитика поиска и добавления в корзину"""
    if event.name == "SEARCH":
        searches = [e for e in state["events"] if e.name == "SEARCH"]
        
        # Группируем по event_id
        event_popularity = {}
        for search in searches:
            event_id = search.payload.get("event_id")
            if event_id:
                event_popularity[event_id] = event_popularity.get(event_id, 0) + 1
        
        return {
            "type": "search_analytics",
            "total_searches": len(searches),
            "event_popularity": event_popularity
        }
    return {}

# Регистрируем новый обработчик
event_bus.subscribe("SEARCH", search_analytics_handler)
# Регистрируем обработчики
event_bus.subscribe("HOLD", hold_analytics_handler)
event_bus.subscribe("PURCHASED", sales_analytics_handler) 
event_bus.subscribe("SCANNED", gate_analytics_handler)