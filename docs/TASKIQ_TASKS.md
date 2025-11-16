# Taskiq Background Tasks

This document describes the background task system for BagTracker using Taskiq.

## Overview

BagTracker uses [Taskiq](https://taskiq-python.github.io/) as a distributed task queue for handling periodic background jobs. The system provides:

- **Periodic balance snapshots** (hourly, daily, weekly, monthly)
- **Transaction recalculation**
- **Automatic cleanup of old snapshots**

## Architecture

```
┌─────────────────┐
│  FastAPI App    │  (Sends tasks to broker)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Redis Broker   │  (Message queue)
└────────┬────────┘
         │
         ├──────────────────┐
         v                  v
┌─────────────────┐  ┌─────────────────┐
│  Taskiq Worker  │  │ Taskiq Scheduler│
│  (Executes      │  │ (Triggers       │
│   tasks)        │  │  scheduled      │
│                 │  │  tasks)         │
└─────────────────┘  └─────────────────┘
```

## Components

### 1. Broker (`backend/taskiq_broker.py`)

Configures the Redis-based broker for task distribution:
- **Broker**: ListQueueBroker connected to Redis
- **Used by**: FastAPI app, workers, and scheduler

### 2. Tasks (`backend/tasks.py`)

Defines the actual background tasks:

#### Scheduled Tasks (Periodic)

- **`create_hourly_snapshots()`**
  - **Schedule**: Every hour at minute :05
  - **Purpose**: Create hourly balance snapshots
  - **Cron**: `5 * * * *`

- **`create_daily_snapshots()`**
  - **Schedule**: Daily at 00:15 UTC
  - **Purpose**: Create daily balance snapshots
  - **Cron**: `15 0 * * *`

- **`create_weekly_snapshots()`**
  - **Schedule**: Sundays at 01:00 UTC
  - **Purpose**: Create weekly balance snapshots
  - **Cron**: `0 1 * * 0`

- **`create_monthly_snapshots()`**
  - **Schedule**: 1st of month at 02:00 UTC
  - **Purpose**: Create monthly balance snapshots
  - **Cron**: `0 2 1 * *`

- **`cleanup_old_snapshots()`**
  - **Schedule**: Daily at 03:00 UTC
  - **Purpose**: Clean up old snapshots based on retention policy
  - **Cron**: `0 3 * * *`
  - **Retention**:
    - Hourly: 7 days (configurable: `BALANCE_HOURLY_RETENTION_DAYS`)
    - Daily/Weekly/Monthly: 90 days (configurable: `BALANCE_HISTORY_RETENTION_DAYS`)

#### Manual Tasks (On-demand)

- **`recalculate_wallet_balances(wallet_id: int, create_snapshots: bool = False)`**
  - Recalculate balances for a specific wallet from transaction history
  - Use for corrections or after data migrations
  - **WARNING**: Expensive operation!

- **`recalculate_all_wallets(create_snapshots: bool = False)`**
  - Recalculate balances for ALL wallets
  - **WARNING**: Very expensive! Use only for system-wide corrections.

### 3. Scheduler (`backend/scheduler.py`)

Sets up the LabelScheduleSource that discovers tasks with schedule labels.

### 4. Docker Services (`docker-compose.yml`)

Two new services are added:

- **`taskiq-worker`**: Executes tasks from the queue
- **`taskiq-scheduler`**: Triggers scheduled tasks at specified times

## Running the System

### Using Docker Compose (Recommended)

```bash
# Start all services (app, db, redis, worker, scheduler)
docker-compose up -d

# View worker logs
docker-compose logs -f taskiq-worker

# View scheduler logs
docker-compose logs -f taskiq-scheduler

# Stop all services
docker-compose down
```

### Manual Execution (Development)

```bash
# Activate virtual environment
source .venv/bin/activate

# Start worker (in one terminal)
taskiq worker backend.taskiq_broker:broker --fs-discover

# Start scheduler (in another terminal)
taskiq scheduler backend.scheduler:scheduler
```

## Triggering Tasks Manually

### From Python Code

```python
from backend.tasks import recalculate_wallet_balances, create_hourly_snapshots

# Trigger wallet recalculation
await recalculate_wallet_balances.kiq(wallet_id=123, create_snapshots=True)

# Trigger hourly snapshot (doesn't wait for scheduled time)
await create_hourly_snapshots.kiq()
```

### From CLI (using taskiq)

```bash
# Send task to queue
taskiq task backend.tasks:recalculate_wallet_balances --args '{"wallet_id": 123, "create_snapshots": false}'
```

## Configuration

Environment variables (in `.env`):

```bash
# Redis connection
REDIS_HOST="redis"
REDIS_PORT=6379
REDIS_DB=0

# Balance snapshot settings
BALANCE_SNAPSHOT_ENABLED=true          # Enable/disable snapshots
BALANCE_HOURLY_SNAPSHOTS=true          # Enable hourly snapshots
BALANCE_DAILY_SNAPSHOTS=true           # Enable daily snapshots
BALANCE_HISTORY_RETENTION_DAYS=90      # Days to keep daily/weekly/monthly
BALANCE_HOURLY_RETENTION_DAYS=7        # Days to keep hourly snapshots
```

## Monitoring

### Check Task Queue

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# List all keys (tasks)
KEYS *

# Check queue length
LLEN taskiq:default:queue
```

### View Task Results

Task results are logged by the worker. Check logs:

```bash
docker-compose logs -f taskiq-worker
```

## Development

### Adding New Tasks

1. **Define task in `backend/tasks.py`**:

```python
@broker.task(
    schedule=[{"cron": "0 4 * * *", "id": "my_custom_task"}],  # Optional schedule
)
async def my_custom_task() -> dict:
    """My custom background task"""
    # Your task logic here
    return {"status": "success"}
```

2. **Import task in `backend/scheduler.py`** (if scheduled):

```python
from backend.tasks import my_custom_task
```

3. **Restart services**:

```bash
docker-compose restart taskiq-worker taskiq-scheduler
```

### Testing Tasks

```python
# Test task directly (without queue)
from backend.tasks import create_hourly_snapshots

result = await create_hourly_snapshots()
print(result)
```

## Troubleshooting

### Worker Not Processing Tasks

1. Check if worker is running:
   ```bash
   docker-compose ps taskiq-worker
   ```

2. Check worker logs:
   ```bash
   docker-compose logs -f taskiq-worker
   ```

3. Verify Redis connection:
   ```bash
   docker-compose exec redis redis-cli PING
   ```

### Scheduled Tasks Not Running

1. Check if scheduler is running:
   ```bash
   docker-compose ps taskiq-scheduler
   ```

2. Check scheduler logs:
   ```bash
   docker-compose logs -f taskiq-scheduler
   ```

3. Verify task schedules in `backend/tasks.py`

### Task Failures

1. Check task logs in worker output
2. Verify database connection (tasks need DB access)
3. Check environment variables are set correctly

## Production Considerations

### Scaling Workers

To handle more tasks concurrently, scale up workers:

```bash
docker-compose up -d --scale taskiq-worker=3
```

### Task Retries

Add retry logic to tasks:

```python
@broker.task(
    schedule=[{"cron": "0 * * * *"}],
    max_retries=3,
    retry_on_error=True,
)
async def my_task() -> dict:
    # Task logic
    pass
```

### Monitoring in Production

Consider adding:
- Sentry integration for error tracking
- Prometheus metrics for task execution
- Dead letter queue for failed tasks

## References

- [Taskiq Documentation](https://taskiq-python.github.io/)
- [Taskiq-Redis](https://github.com/taskiq-python/taskiq-redis)
- [Cron Expression Format](https://crontab.guru/)
