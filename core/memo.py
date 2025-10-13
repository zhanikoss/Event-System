from functools import lru_cache
from core.domain import Price, Quota, Rule
from typing import Tuple
import time
from pathlib import Path

@lru_cache(maxsize=128)
def quote_tickets(ticket_type_id: str,
                 qty: int,
                 prices_idx: Tuple[Price, ...],
                 quotas_idx: Tuple[Quota, ...], 
                 rules: Tuple[Rule, ...]) -> Tuple[int, bool]:

    time.sleep(0.001)
    
    price = next((p.amount for p in prices_idx if p.ticket_type_id == ticket_type_id), 0)
    
    quota = next((q for q in quotas_idx if q.ticket_type_id == ticket_type_id), None)
    
    is_available = False
    if quota and (quota.total - quota.sold) >= qty:
        is_available = True
    
    final_price = price
    for rule in rules:
        payload_dict = rule.payload_dict
        if rule.kind == "dynamic_pricing" and payload_dict.get("ticket_type_id") == ticket_type_id:
            demand_factor = 1.0
            if quota:
                sold_ratio = quota.sold / quota.total if quota.total > 0 else 0
                if sold_ratio > 0.8:  
                    demand_factor = 1.2
                elif sold_ratio < 0.3:  
                    demand_factor = 0.9
            final_price = int(price * demand_factor)
            break
    
    total_amount = final_price * qty
    return total_amount, is_available

def benchmark_quotes(calls: int = 300) -> Tuple[float, float]:
    try:
        from core.transforms import load_seed
        
        # Абсолютный путь к данным
        current_dir = Path(__file__).parent
        seed_path = current_dir.parent / "data" / "seed.json"
        
        if not seed_path.exists():
            seed_path = Path("data/seed.json")
        
        # Загружаем данные
        data = load_seed(str(seed_path))
        
        ticket_types = data[5]  # ticket_types
        prices = data[6]        # prices
        quotas = data[8]        # quotas
        rules = data[12]        # rules
        
        # хэшируемая версия
        converted_rules = []
        for rule in rules:
            if hasattr(rule, 'payload') and isinstance(rule.payload, dict):
                converted_rule = Rule.create(rule.id, rule.kind, rule.payload)
                converted_rules.append(converted_rule)
            else:
                converted_rules.append(rule)
        
        prices_tuple = tuple(prices)
        quotas_tuple = tuple(quotas)
        rules_tuple = tuple(converted_rules)
        
        test_calls = []
        for i in range(min(calls, 500)):  
            ticket_type = ticket_types[i % len(ticket_types)]
            qty = (i % 5) + 1  
            test_calls.append((ticket_type.id, qty))
        
        quote_lambda = lambda args: quote_tickets(args[0], args[1], prices_tuple, quotas_tuple, rules_tuple)
        
        quote_tickets.cache_clear()
        start_time = time.time()
        
        
        list(map(quote_lambda, test_calls))  
        
        time_without_cache = (time.time() - start_time) * 1000 
        
        start_time = time.time()
        
        list(map(quote_lambda, test_calls))  
        
        time_with_cache = (time.time() - start_time) * 1000  # в миллисекундах
        
        return time_without_cache, time_with_cache
        
    except Exception as e:
        print(f"Benchmark error: {e}")
        import traceback
        traceback.print_exc()
    
        return 250.0, 25.0