# BagTracker Test Suite

## Overview

This test suite provides comprehensive coverage for the BagTracker application, including:

- **Database Models**: Tests for Base model CRUD operations, soft delete, dual ID strategy, serialization
- **Managers**: Tests for all CRUD managers (User, Wallet, Transaction, Balance, etc.)
- **Business Logic**: Tests for transaction processing, balance calculations, eager loading

## Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── README.md                   # This file
├── test_models/               # Database model tests
│   ├── __init__.py
│   └── test_base.py           # Base model methods (save, delete, get, etc.)
└── test_managers/             # Manager tests
    ├── __init__.py
    ├── test_base_crud.py      # BaseCRUDManager tests
    ├── test_users.py          # UserManager tests
    ├── test_wallets.py        # WalletManager tests
    ├── test_transactions.py   # TransactionManager tests
    └── test_balance.py        # BalanceManager tests
```

## Prerequisites

### Required Database: PostgreSQL with TimescaleDB

**⚠️ CRITICAL:** This test suite **REQUIRES** PostgreSQL with the TimescaleDB extension. SQLite is **NOT** supported.

**Why PostgreSQL is Required:**

1. **TimescaleDB Hypertables**: The project uses TimescaleDB hypertables for:
   - `balances_history`
   - `nft_balances_history`
   - `cex_balances_history`

2. **PostgreSQL-Specific Features**:
   - `gen_random_uuid()` function for UUID generation
   - Composite primary keys with autoincrement in hypertables
   - Partial indexes with `WHERE` clauses
   - PostgreSQL regex operators (`~`)

3. **Data Precision**: Uses `Numeric(38, 18)` for financial calculations

## Setup Instructions

### Option 1: Using Docker (Recommended)

#### Start PostgreSQL with TimescaleDB:

```bash
# Using Docker
docker run -d \
  --name bagtracker-test-db \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=Pa55w0rD \
  -e POSTGRES_DB=bagtracker_test \
  timescale/timescaledb:latest-pg14

# Wait a few seconds for DB to be ready
sleep 5

# Verify it's running
docker ps | grep bagtracker-test-db
```

#### Using docker-compose (if available):

```bash
# Start database services
docker-compose up -d db
```

### Option 2: Local PostgreSQL Installation

If you prefer a local PostgreSQL installation:

1. **Install PostgreSQL 14+**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql-14 postgresql-client-14

   # macOS (using Homebrew)
   brew install postgresql@14
   ```

2. **Install TimescaleDB Extension**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install timescaledb-2-postgresql-14

   # macOS
   brew tap timescale/tap
   brew install timescaledb
   timescaledb-tune
   ```

3. **Create Test Database**:
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql

   # Create database
   CREATE DATABASE bagtracker_test;

   # Enable TimescaleDB extension
   \c bagtracker_test
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```

### Environment Configuration

Create or update `.env` with test database URL:

```bash
# Add this to your .env file for testing
TEST_DATABASE_URL="postgresql+asyncpg://postgres:Pa55w0rD@localhost:5432/bagtracker_test"
```

Or export it before running tests:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:Pa55w0rD@localhost:5432/bagtracker_test"
```

## Running Tests

### Install Dependencies

```bash
# Using UV (recommended)
uv venv
uv sync --group dev

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_models/test_base.py

# Run specific test class
pytest tests/test_managers/test_users.py::TestUserManagerCreateUser

# Run specific test
pytest tests/test_managers/test_users.py::TestUserManagerCreateUser::test_create_user_success
```

### Useful pytest Options

```bash
# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run only tests that failed last time
pytest --lf

# Show print statements
pytest -s

# Generate HTML coverage report
pytest --cov=backend --cov-report=html
# View coverage: open htmlcov/index.html
```

## Test Fixtures

The test suite provides comprehensive fixtures in `conftest.py`:

### Database Fixtures

- `test_engine`: Session-scoped test database engine
- `async_session`: Function-scoped async database session with automatic rollback
- `db_session`: Alias for `async_session`

### Factory Fixtures

Create test data easily:

```python
async def test_example(async_session, user_factory, wallet_factory):
    # Create a test user
    user = user_factory(username="testuser")
    await user.save(async_session)

    # Create a test wallet for the user
    wallet = wallet_factory(user.id, wallet_type="metamask")
    await wallet.save(async_session)
```

Available factories:

- `user_factory()`: Create User instances
- `chain_factory()`: Create Chain instances
- `token_factory(chain_id)`: Create Token instances
- `wallet_factory(user_id)`: Create Wallet instances
- `wallet_address_factory(wallet_id, chain_id)`: Create WalletAddress instances
- `transaction_factory(wallet_id, token_id, chain_id)`: Create Transaction instances
- `balance_factory(wallet_id, token_id, chain_id)`: Create Balance instances
- `portfolio_factory(user_id)`: Create Portfolio instances

## Test Coverage

### Current Coverage Areas

✅ **Database Models (Base)**:
- CRUD operations (save, create, update, upsert, delete)
- Soft delete and restore
- Hard delete
- Dual ID strategy (id and uuid)
- Retrieval methods (get_by_id, get_by_uuid, get_one, get_all)
- Serialization (to_dict, to_json)
- Decimal handling

✅ **Managers (BaseCRUDManager)**:
- Generic CRUD operations
- Eager loading relationships
- User-specific helpers
- Schema-based operations

✅ **UserManager**:
- User creation with password hashing
- Duplicate username/email validation
- User retrieval (by username, UUID, email)
- User updates (full and partial)
- Eager loading of wallets and portfolios

✅ **WalletManager**:
- Multichain wallet creation
- Adding/removing chains
- Finding wallets by address
- Address case-insensitive lookups
- Eager loading of addresses and transactions

✅ **TransactionManager**:
- Transaction creation (wallet and CEX)
- Bulk transaction creation
- Transaction updates
- Transaction cancellation
- Transaction deletion with balance recalculation

✅ **BalanceManager**:
- Wallet balance retrieval
- Balance filtering (by chain, exclude zero)
- Total value calculations
- Balance recalculation

### Not Yet Covered

❌ Areas that need additional tests:
- Integration tests with actual balance calculations
- Price update mechanisms
- History snapshot creation
- CEX-related functionality
- NFT balance tracking
- Portfolio management
- Authentication/JWT
- External API integrations (Web3, CoinGecko)

## Troubleshooting

### "ConnectionRefusedError: Connect call failed"

**Cause**: PostgreSQL is not running or not accessible.

**Solution**:
1. Start PostgreSQL: `docker start bagtracker-test-db`
2. Check if running: `docker ps | grep postgres`
3. Verify connection: `pg_isready -h localhost -p 5432`

### "No module named 'timescaledb'"

**Cause**: TimescaleDB extension not installed.

**Solution**:
- For Docker: Use `timescale/timescaledb:latest-pg14` image
- For local installation: Install timescaledb package

### "Table does not exist"

**Cause**: Database migrations not run or database not initialized.

**Solution**:
The test suite automatically creates and drops tables for each test session.
If you encounter this error, the database connection may be failing.

### Tests are slow

**Cause**: Database operations and test isolation.

**Solutions**:
- Use `pytest -n auto` for parallel execution (requires `pytest-xdist`)
- Use session-scoped fixtures where appropriate
- Consider using database transactions for faster rollback

### Import errors

**Cause**: Missing dependencies or virtual environment not activated.

**Solution**:
```bash
source .venv/bin/activate
uv sync --group dev
```

## Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `TestFeatureName`
- Test methods: `test_what_it_does`

### Example Test

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
class TestMyFeature:
    """Test my feature."""

    async def test_feature_works(self, async_session: AsyncSession, user_factory):
        """Test that the feature works correctly."""
        # Arrange
        user = user_factory(username="testuser")
        await user.save(async_session)

        # Act
        result = await some_operation(user)

        # Assert
        assert result is not None
        assert result.id == user.id
```

### Best Practices

1. **Use factories**: Don't create models manually
2. **Test isolation**: Each test should be independent
3. **Use descriptive names**: Test names should explain what they test
4. **Test both success and failure**: Test error cases too
5. **Keep tests focused**: One test should test one thing
6. **Use async/await**: All database operations must be async
7. **Clean up**: Use fixtures and session rollback for cleanup

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: Pa55w0rD
          POSTGRES_DB: bagtracker_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: |
          uv venv
          uv sync --group dev

      - name: Run tests
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://postgres:Pa55w0rD@localhost:5432/bagtracker_test
        run: |
          source .venv/bin/activate
          pytest --cov=backend --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```
