import pytest
import asyncio
from datetime import datetime, timedelta
from core.async_ops import parallel_event_analysis, real_time_data_stream, progressive_calculation
from core.domain import Event

pytest_plugins = "pytest_asyncio"

@pytest.fixture
def sample_events():
    now = datetime.now()
    e1 = Event(id="1", title="Concert", hall_id="H1", start=now, end=now + timedelta(hours=2))
    e2 = Event(id="2", title="Play", hall_id="H2", start=now, end=now + timedelta(hours=1, minutes=30))
    return [e1, e2]

@pytest.mark.asyncio
async def test_progressive_calculation_yields_steps():
    steps = []
    count = 0
    async for step in progressive_calculation():
        steps.append(step)
        count += 1
        if count >= 3:  # Stop after 3 steps
            break
    assert len(steps) > 0

@pytest.mark.asyncio
async def test_real_time_data_stream_yields_data():
    batches = []
    count = 0
    async for batch in real_time_data_stream():
        batches.append(batch)
        count += 1
        if count >= 2:  # Stop after 2 batches
            break
    assert len(batches) > 0

@pytest.mark.asyncio
async def test_parallel_event_analysis_returns_results(sample_events):
    results = []
    async for msg, res, completed, total in parallel_event_analysis(sample_events):
        results.append(res)
        if completed == total:  # Stop when done
            break
    assert len(results) > 0

@pytest.mark.asyncio
async def test_parallel_event_analysis_progress_count(sample_events):
    completed_steps = 0
    total_tasks = 0
    async for msg, res, completed, total in parallel_event_analysis(sample_events):
        completed_steps = completed
        total_tasks = total
        if completed == total:  # Stop when done
            break
    assert completed_steps == total_tasks

@pytest.mark.asyncio
async def test_real_time_data_stream_keys():
    count = 0
    async for data in real_time_data_stream():
        assert "gate" in data
        assert "batch" in data
        assert "visitors" in data
        count += 1
        if count >= 1:  # Stop after first item
            break