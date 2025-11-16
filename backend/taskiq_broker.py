"""
Taskiq broker configuration for background tasks.

This module sets up the Taskiq broker using Redis as the message backend.
It provides a centralized broker instance for task scheduling and execution.
"""

from taskiq import TaskiqScheduler
from taskiq_redis import ListQueueBroker, RedisScheduleSource

from backend.settings import settings

# Initialize the broker with Redis
broker = ListQueueBroker(url=settings.redis_url)

# Initialize the scheduler with Redis as the schedule source
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[RedisScheduleSource(url=settings.redis_url)],
)
