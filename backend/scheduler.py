"""
Task scheduler configuration.

This module sets up the schedule source for Taskiq.
The actual task schedules are defined using labels on the tasks themselves.

To start the scheduler:
    taskiq scheduler backend.scheduler:scheduler
"""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from backend.taskiq_broker import broker

# Create scheduler with label-based schedule source
# Tasks with schedule labels will be automatically picked up
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

# The scheduler will discover tasks with @broker.task decorators that have
# schedule labels. See backend/tasks.py for task definitions.

# To manually trigger tasks programmatically:
# from backend.tasks import recalculate_wallet_balances
# await recalculate_wallet_balances.kiq(wallet_id=123)
