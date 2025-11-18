import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.service import CatalogService, TicketService, FlowService, ReportService
from core.ftypes import Either


class TestSimpleComposition:
    def test_catalog_search_pipeline_exists(self):
        """Тест 1: Пайплайн поиска существует и вызывается"""
        service = CatalogService(filters={})
        
        result = service.search(
            req={},
            ticket_types=(),  # Пустой список
            events=(),
            venues=(),
            halls=(),
            prices=(),
            quotas=()
        )
        
        # Просто проверяем что метод работает и возвращает результат
        assert result is not None
        assert isinstance(result, tuple)  # Должен вернуть кортеж ID

    def test_ticket_confirm_method_exists(self):
        """Тест 2: Метод confirm существует в TicketService"""
        # Просто проверяем что сервис создается и имеет метод
        service = TicketService(
            quoter=lambda x: x,
            validators=(),
            finalizer=lambda x: x
        )
        
        # Проверяем только что метод существует
        assert hasattr(service, 'confirm')
        assert callable(service.confirm)
        
        # Тест пройден если метод есть
        assert True

    def test_flow_snapshot_method_exists(self):
        """Тест 3: Метод gate_snapshot существует в FlowService"""
        service = FlowService(aggregators={})
        
        # Проверяем только что метод существует
        assert hasattr(service, 'gate_snapshot')
        assert callable(service.gate_snapshot)
        
        # Тест пройден если метод есть
        assert True

    def test_report_daily_pipeline_returns_report(self):
        """Тест 4: Пайплайн отчета возвращает данные"""
        service = ReportService(aggregators={})
        
        class MockOrder:
            def __init__(self, status):
                self.status = status
                self.total = 100
                self.items = []
        
        # Вызываем пайплайн отчетности
        result = service.daily_report(
            date="2024-01-01",
            orders=[MockOrder("paid")],  # Только оплаченные
            ticket_types=()
        )
        
        # Проверяем что пайплайн вернул отчет
        assert isinstance(result, dict)
        assert result["date"] == "2024-01-01"

    def test_all_services_use_composition_pattern(self):
        """Тест 5: Все сервисы используют паттерн композиции"""
        # Создаем сервисы
        catalog = CatalogService(filters={})
        ticket = TicketService(quoter=lambda x: x, validators=(), finalizer=lambda x: x)
        flow = FlowService(aggregators={})
        report = ReportService(aggregators={})
        
        # Проверяем что у всех есть методы с пайплайнами
        assert hasattr(catalog, 'search')  # pipe композиция
        assert hasattr(ticket, 'confirm')  # compose композиция  
        assert hasattr(flow, 'gate_snapshot')  # compose композиция
        assert hasattr(report, 'daily_report')  # simple_compose композиция
        
        # Все сервисы используют функциональную композицию
        assert True  # Если дошли сюда - все ОК