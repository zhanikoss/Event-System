from typing import Callable, Dict, List, Any, NamedTuple
from collections import defaultdict
from datetime import datetime
import threading

class EventMsg(NamedTuple):
    name: str
    ts: str
    payload: Dict[str, Any]

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._event_history = []
        self._lock = threading.Lock()
    
    def subscribe(self, name: str, handler: Callable[[EventMsg, Dict], Dict]):
        """Подписка на события"""
        with self._lock:
            self._subscribers[name].append(handler)
    
    def publish(self, name: str, payload: Dict):
        """Публикация события"""
        event = EventMsg(
            name=name,
            ts=datetime.now().isoformat(),
            payload=payload
        )
        
        with self._lock:
            self._event_history.append(event)
            
            # Вызываем всех подписчиков
            results = []
            for handler in self._subscribers.get(name, []):
                try:
                    result = handler(event, self.get_current_state())
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Handler error: {e}")
            
            return results
    
    def get_current_state(self) -> Dict[str, Any]:
        """Текущее состояние системы"""
        return {
            "events": self._event_history[-100:],  # последние 100 событий
            "stats": self._calculate_stats()
        }
    
    def _calculate_stats(self) -> Dict[str, Any]:
        """Чистая функция для расчета статистики"""
        holds = [e for e in self._event_history if e.name == "HOLD"]
        purchases = [e for e in self._event_history if e.name == "PURCHASED"]
        scans = [e for e in self._event_history if e.name == "SCANNED"]
        
        return {
            "active_holds": len([h for h in holds if self._is_hold_active(h)]),
            "total_purchases": len(purchases),
            "total_revenue": sum(p.payload.get("amount", 0) for p in purchases),
            "total_scans": len(scans),
            "successful_scans": len([s for s in scans if s.payload.get("ok", False)]),
        }
    
    def _is_hold_active(self, hold_event: EventMsg) -> bool:
        """Проверяет активен ли холд (TTL 10 минут)"""
        hold_time = datetime.fromisoformat(hold_event.ts)
        current_time = datetime.now()
        return (current_time - hold_time).total_seconds() < 600  # 10 минут

# Глобальная шина событий
event_bus = EventBus()