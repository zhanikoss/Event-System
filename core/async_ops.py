import asyncio
from datetime import datetime
from typing import List, Dict
import streamlit as st

from core.domain import Event

async def parallel_event_analysis(events: List[Event]):
    """
    Асинхронный анализ событий: финансы, посещаемость, вместимость.
    Результаты приходят по мере готовности.
    """
    result_queue = asyncio.Queue()
    total_tasks = 0
    completed = 0

    async def analyze_financial(event: Event):
        await asyncio.sleep(0.5)
        event_orders = [o for o in st.session_state.orders if o.event_id == event.id]
        paid_orders = [o for o in event_orders if o.status == "paid"]
        result = {
            "event_id": event.id,
            "event_title": event.title,
            "type": "financial",
            "ready_at": datetime.now().isoformat(),
            "revenue": sum(o.total for o in paid_orders),
            "tickets_sold": sum(len(o.items) for o in paid_orders),
            "avg_ticket_price": sum(o.total for o in paid_orders) / max(len(paid_orders), 1)
        }
        await result_queue.put(("💰 FINANCE READY", result))

    async def analyze_attendance(event: Event):
        await asyncio.sleep(1.5)
        event_scans = [s for s in st.session_state.scans
                      if any(o.event_id == event.id for o in st.session_state.orders
                             if o.id == s.order_id)]
        result = {
            "event_id": event.id,
            "event_title": event.title,
            "type": "attendance",
            "ready_at": datetime.now().isoformat(),
            "total_scans": len(event_scans),
            "successful_scans": len([s for s in event_scans if s.ok])
        }
        await result_queue.put(("🎫 ATTENDANCE READY", result))

    async def analyze_capacity(event: Event):
        await asyncio.sleep(2.5)
        hall = next((h for h in st.session_state.halls if h.id == event.hall_id), None)
        event_orders = [o for o in st.session_state.orders if o.event_id == event.id]
        tickets_sold = sum(len(o.items) for o in event_orders)
        utilization = (tickets_sold / hall.capacity * 100) if hall and hall.capacity else 0
        result = {
            "event_id": event.id,
            "event_title": event.title,
            "type": "capacity",
            "ready_at": datetime.now().isoformat(),
            "tickets_sold": tickets_sold,
            "capacity": hall.capacity if hall else 0,
            "utilization": utilization
        }
        await result_queue.put(("🏟️ CAPACITY READY", result))

    # собираем все задачи
    tasks = []
    for event in events:
        tasks.extend([
            analyze_financial(event),
            analyze_attendance(event),
            analyze_capacity(event)
        ])

    total_tasks = len(tasks)
    gather = asyncio.gather(*tasks)  # корутина для выполнения всех задач одновременно

    # собираем результаты по мере готовности
    while completed < total_tasks:
        message, result = await result_queue.get()
        completed += 1
        yield message, result, completed, total_tasks

    # ждём завершения всех задач
    await gather

async def real_time_data_stream():
    """
    Генерация событий ворот по мере готовности
    """
    gates = [
        ("🚪 FAST Gate", 0.3),
        ("🚪 MEDIUM Gate", 0.8),
        ("🚪 SLOW Gate", 1.5),
    ]
    for gate_name, delay in gates:
        for i in range(3):
            await asyncio.sleep(delay)
            yield {
                "gate": gate_name,
                "batch": i + 1,
                "visitors": (i + 1) * 10,
                "timestamp": datetime.now().isoformat(),
                "delay": delay
            }

async def progressive_calculation():
    """
    Прогрессивный расчёт с промежуточными результатами
    """
    steps = [
        ("🔍 Loading data...", 0.5),
        ("💰 Calculating finances...", 1.0),
        ("🎫 Analyzing attendance...", 1.5),
        ("📊 Generating report...", 0.8),
    ]
    for step_name, step_time in steps:
        await asyncio.sleep(step_time)
        yield {
            "step": step_name,"progress": steps.index((step_name, step_time)) + 1,
            "total_steps": len(steps),
            "timestamp": datetime.now().isoformat()
        }

def run_async_generator(async_gen_func, *args):
    """
    Запуск асинхронного генератора в синхронном коде Streamlit
    """
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio

    results = []
    async def collect():
        async for item in async_gen_func(*args):
            results.append(item)
    asyncio.get_event_loop().run_until_complete(collect())
    return results