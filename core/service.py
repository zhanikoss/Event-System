from typing import Tuple, Dict, Callable, Any, List
from core.domain import TicketType, Order, Scan, Event, Venue, Hall, Price, Quota
from core.ftypes import Either
from core.compose import compose, pipe

class CatalogService:
    def __init__(self, filters: Dict[str, Callable]):
        self.filters = filters
    
    def search(self, req: Dict, ticket_types: Tuple[TicketType, ...], 
               events: Tuple[Event, ...], venues: Tuple[Venue, ...], 
               halls: Tuple[Hall, ...], prices: Tuple[Price, ...], 
               quotas: Tuple[Quota, ...]) -> Tuple[str, ...]:
        """Ticket search through filter composition"""
        
        def filter_by_city(tickets: List[TicketType]) -> List[TicketType]:
            if not req.get('city') or req['city'] == "All":
                return tickets
            
            from core.filters import by_city
            city_filter = by_city(req['city'])
            
            filtered_events = city_filter(events, venues, halls)
            event_ids = {e.id for e in filtered_events}
            
            return [t for t in tickets if t.event_id in event_ids]
        
        def filter_by_price(tickets: List[TicketType]) -> List[TicketType]:
            if not req.get('price_range'):
                return tickets
            
            min_price, max_price = req['price_range']
            filtered = []
            for ticket in tickets:
                price = next((p.amount for p in prices 
                            if p.ticket_type_id == ticket.id), 0)
                if min_price <= price <= max_price:
                    filtered.append(ticket)
            return filtered
        
        def filter_by_availability(tickets: List[TicketType]) -> List[TicketType]:
            filtered = []
            for ticket in tickets:
                quota = next((q for q in quotas 
                            if q.ticket_type_id == ticket.id), None)
                if quota and (quota.total - quota.sold) > 0:
                    filtered.append(ticket)
            return filtered
        
        def get_ticket_ids(tickets: List[TicketType]) -> Tuple[str, ...]:
            return tuple(t.id for t in tickets)
        
        # Filter composition via pipe
        search_pipeline = pipe(
            list(ticket_types),
            filter_by_city,
            filter_by_price, 
            filter_by_availability,
            get_ticket_ids
        )
        
        return search_pipeline

class TicketService:
    def __init__(self, quoter: Callable, validators: Tuple[Callable, ...], finalizer: Callable):
        self.quoter = quoter
        self.validators = validators
        self.finalizer = finalizer
    
    def confirm(self, order: Order, quotas: Tuple[Quota, ...], 
                ticket_types: Tuple[TicketType, ...], events: Tuple[Event, ...],
                prices: Tuple[Price, ...], user_age: int = None) -> Either[Dict, Order]:  # ✅ ДОБАВИЛ user_age
        """Order confirmation through validation pipeline"""
        
        def validate_quotas(order: Order) -> Either[Dict, Order]:
            for item in order.items:
                quota = next((q for q in quotas 
                            if q.ticket_type_id == item.ticket_type_id), None)
                if not quota or (quota.total - quota.sold) < item.qty:
                    return Either.left({
                        "error": "Not enough tickets available",
                        "ticket_type_id": item.ticket_type_id,
                        "available": quota.total - quota.sold if quota else 0,
                        "requested": item.qty
                    })
            return Either.right(order)
        
        def validate_age(order: Order) -> Either[Dict, Order]:
            # Age restriction check - используем переданный user_age
            age_restricted_events = []
            for item in order.items:
                ticket = next((t for t in ticket_types 
                             if t.id == item.ticket_type_id), None)
                if ticket:
                    event = next((e for e in events 
                                if e.id == ticket.event_id), None)
                    if event and ("Rock" in event.title or "Festival" in event.title):
                        age_restricted_events.append(event.title)
            
            # ✅ ИСПОЛЬЗУЕМ user_age из параметров, а не из order
            if age_restricted_events and user_age and user_age < 18:
                return Either.left({
                    "error": "Age restriction",
                    "message": f"Events {age_restricted_events} require 18+ age",
                    "user_age": user_age  # ✅ используем параметр
                })
            return Either.right(order)
        
        def apply_pricing(order: Order) -> Either[Dict, Order]:
            # Apply dynamic pricing
            total = 0
            for item in order.items:
                base_price = next((p.amount for p in prices 
                                if p.ticket_type_id == item.ticket_type_id), 0)
                
                # Simple rule: VIP tickets are more expensive
                ticket = next((t for t in ticket_types 
                             if t.id == item.ticket_type_id), None)
                if ticket and "VIP" in ticket.title:
                    base_price = int(base_price * 1.2)  # +20% for VIP
                
                total += base_price * item.qty
            
            # Create updated order with new price
            updated_order = Order(
                id=order.id,
                event_id=order.event_id,
                items=order.items,
                total=total,
                status="confirmed"
            )
            return Either.right(updated_order)
        
        def finalize_order(order: Order) -> Either[Dict, Order]:
            # Final order processing
            finalized_order = Order(
                id=order.id,
                event_id=order.event_id, 
                items=order.items,
                total=order.total,
                status="paid"
            )
            return Either.right(finalized_order)
        
        # Order confirmation pipeline composition
        confirmation_pipeline = compose(
            finalize_order,
            apply_pricing,
            validate_age,
            validate_quotas
        )
        
        return confirmation_pipeline(order)

class FlowService:
    def __init__(self, aggregators: Dict[str, Callable]):
        self.aggregators = aggregators
    
    def gate_snapshot(self, gate_id: str, now: str, scans: Tuple[Scan, ...]) -> Dict:
        """Gate status snapshot through aggregator composition"""
        
        def get_gate_scans() -> List[Scan]:
            return [s for s in scans if s.gate_id == gate_id]
        
        def calculate_metrics(scans: List[Scan]) -> Dict[str, Any]:
            total_scans = len(scans)
            successful_scans = len([s for s in scans if s.ok])
            
            # Hourly analysis
            hourly_stats = {}
            for scan in scans:
                try:
                    hour = scan.ts.split('T')[1].split(':')[0] + ":00"
                    hourly_stats[hour] = hourly_stats.get(hour, 0) + 1
                except (IndexError, AttributeError):
                    continue
            
            return {
                "gate_id": gate_id,
                "total_scans": total_scans,
                "successful_scans": successful_scans,
                "success_rate": (successful_scans / total_scans * 100) if total_scans > 0 else 0,
                "hourly_activity": hourly_stats,
                "timestamp": now
            }
        
        def enrich_with_alerts(metrics: Dict[str, Any]) -> Dict[str, Any]:
            # Add alerts if low success rate
            if metrics["success_rate"] < 80 and metrics["total_scans"] > 10:
                metrics["alerts"] = ["Low success rate detected"]
            else:
                metrics["alerts"] = []
            return metrics
        
        # Gate data processing pipeline
        analysis_pipeline = compose(
            enrich_with_alerts,
            calculate_metrics, 
            get_gate_scans
        )
        
        return analysis_pipeline()

class ReportService:
    def __init__(self, aggregators: Dict[str, Callable]):
        self.aggregators = aggregators
    
    def daily_report(self, date: str, orders: Tuple[Order, ...], 
                    ticket_types: Tuple[TicketType, ...]) -> Dict:
        """Daily report through aggregator composition"""
        
        # ✅ ПРОСТАЯ КОМПОЗИЦИЯ 
        def simple_compose(*funcs):
            def composed(x):
                result = x
                for f in reversed(funcs):
                    result = f(result)
                return result
            return composed
        
        def get_daily_orders(x):
            """Получаем заказы за день - ВОЗВРАЩАЕТ список заказов"""
            return [o for o in orders if o.status == "paid"]
        
        def calculate_sales_metrics(orders_list):
            """Расчет метрик - ПРИНИМАЕТ список заказов"""
            total_revenue = sum(o.total for o in orders_list)
            total_tickets = sum(len(o.items) for o in orders_list)
            
            ticket_type_sales = {}
            for order in orders_list:
                for item in order.items:
                    ticket_type = next((t for t in ticket_types 
                                      if t.id == item.ticket_type_id), None)
                    if ticket_type:
                        key = ticket_type.title
                        ticket_type_sales[key] = ticket_type_sales.get(key, 0) + item.qty
            
            return {
                "date": date,
                "total_revenue": total_revenue,
                "total_tickets_sold": total_tickets,
                "average_ticket_price": total_revenue / total_tickets if total_tickets > 0 else 0,
                "ticket_type_breakdown": ticket_type_sales,
                "number_of_orders": len(orders_list)
            }
        
        def add_comparison_metrics(metrics):
            """Добавляем сравнения - ПРИНИМАЕТ метрики"""
            if metrics["total_revenue"] > 50000:
                metrics["revenue_trend"] = "excellent"
                metrics["performance_rating"] = "⭐️⭐️⭐️⭐️⭐️"
            elif metrics["total_revenue"] > 20000:
                metrics["revenue_trend"] = "good" 
                metrics["performance_rating"] = "⭐️⭐️⭐️⭐️"
            else:
                metrics["revenue_trend"] = "needs improvement"
                metrics["performance_rating"] = "⭐️⭐️⭐️"
            return metrics
        
        # ✅ СОЗДАЕМ ПАЙПЛАЙН И СРАЗУ ВЫЗЫВАЕМ С ПАРАМЕТРОМ
        report_pipeline = simple_compose(
            add_comparison_metrics,
            calculate_sales_metrics, 
            get_daily_orders
        )
        
        # ✅ ВЫЗЫВАЕМ ПАЙПЛАЙН С НАЧАЛЬНЫМ ЗНАЧЕНИЕМ
        return report_pipeline(None)  # Передаем None как начальное значение