import pytest
from core.frp import EventMsg
from core.frp_handlers import hold_analytics_handler, sales_analytics_handler, gate_analytics_handler

class TestFRPHandlers:
    
    def test_hold_analytics_handler(self):
        """Тест обработчика холдов"""
        event = EventMsg("HOLD", "2024-01-01T10:00:00", {"quantity": 2})
        state = {
            "stats": {"active_holds": 3, "total_revenue": 5000},
            "events": [event, event]  # 2 холда
        }
        
        result = hold_analytics_handler(event, state)
        
        assert result["type"] == "hold_analytics"
        assert result["active_holds"] == 3
        assert result["total_holds"] == 2
    
    def test_sales_analytics_handler(self):
        """Тест обработчика продаж"""
        event = EventMsg("PURCHASED", "2024-01-01T10:00:00", {"amount": 1000})
        state = {
            "stats": {"total_revenue": 5000},
            "events": [event, event]  # 2 покупки
        }
        
        result = sales_analytics_handler(event, state)
        
        assert result["type"] == "sales_analytics"
        assert result["total_revenue"] == 5000
        assert "hourly_sales" in result
    
    def test_gate_analytics_handler(self):
        """Тест обработчика ворот"""
        event = EventMsg("SCANNED", "2024-01-01T10:00:00", {"gate_id": "Main_Entrance", "ok": True})
        state = {
            "stats": {"total_scans": 5, "successful_scans": 4},
            "events": [event]
        }
        
        result = gate_analytics_handler(event, state)
        
        assert result["type"] == "gate_analytics"
        assert result["success_rate"] == 0.8  # 4/5
        assert "gate_stats" in result
    
    def test_handler_ignores_wrong_events(self):
        """Тест что обработчики игнорируют ненужные события"""
        event = EventMsg("WRONG_EVENT", "2024-01-01T10:00:00", {})
        state = {"stats": {}, "events": []}
        
        # Все обработчики должны вернуть пустой словарь
        assert hold_analytics_handler(event, state) == {}
        assert sales_analytics_handler(event, state) == {}
        assert gate_analytics_handler(event, state) == {}
    
    def test_pure_functions(self):
        """Тест что обработчики - чистые функции"""
        event = EventMsg("PURCHASED", "2024-01-01T10:00:00", {"amount": 1000})
        state = {"stats": {"total_revenue": 1000}, "events": [event]}
        
        # Первый вызов
        result1 = sales_analytics_handler(event, state)
        # Второй вызов с теми же данными
        result2 = sales_analytics_handler(event, state)
        
        # Результаты должны быть одинаковыми
        assert result1 == result2
        # Исходное состояние не должно измениться
        assert state["stats"]["total_revenue"] == 1000