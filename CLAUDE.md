# CLAUDE.md - BagTracker AI Assistant Guide

**Version:** 0.0.12
**Last Updated:** 2025-11-15
**Project:** BagTracker - Cryptocurrency Portfolio Tracker

This document provides comprehensive guidance for AI assistants working with the BagTracker codebase.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Directory Structure](#directory-structure)
5. [Database Design](#database-design)
6. [API Design](#api-design)
7. [Development Workflow](#development-workflow)
8. [Code Conventions](#code-conventions)
9. [Security Practices](#security-practices)
10. [Common Tasks](#common-tasks)
11. [Testing Guidelines](#testing-guidelines)
12. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Project Overview

BagTracker is a **production-grade cryptocurrency portfolio tracking system** that helps users monitor their holdings across multiple blockchains and centralized exchanges.

### Key Features
- **Multi-chain wallet tracking**: Ethereum, BSC, Polygon, Arbitrum, Tron, Solana, Stacks
- **FIFO cost basis calculation**: Professional-grade balance tracking with audit trail
- **CEX integration**: Support for centralized exchange accounts
- **NFT tracking**: ERC721/ERC1155 support
- **Real-time price updates**: CoinGecko integration
- **Balance history**: Time-series snapshots (hourly, daily, weekly, monthly)
- **Encrypted credentials**: Fernet encryption for API keys and sensitive data
- **Multi-user system**: User authentication and portfolio management

### Project Maturity
- **Status**: Production-capable, actively developed
- **Code Quality**: Well-architected, type-safe, documented
- **Test Coverage**: Minimal (improvement needed)
- **Security**: Enterprise-grade (encryption, Argon2 hashing, dual ID strategy)

---

## Tech Stack

### Core Framework
- **Python 3.12+**: Required minimum version
- **FastAPI 0.118.3+**: Modern async web framework with auto-generated OpenAPI docs
- **Uvicorn 0.37.0+**: ASGI server with multi-worker support
- **Pydantic 2.x**: Data validation and settings management

### Database
- **PostgreSQL**: Primary database (production)
- **SQLAlchemy 2.0.44+**: Async ORM with declarative models
- **Alembic 1.17.0+**: Database migration management
- **Redis 5.3.1**: Caching and session storage
- **asyncpg 0.30.0+**: Async PostgreSQL driver
- **psycopg 3.2.10+**: Sync PostgreSQL driver (migrations only)

### Blockchain Integration
- **Web3.py 7.13.0+**: Ethereum and EVM chain interaction
- Supports both EVM and non-EVM chains
- Custom providers for multi-chain support

### Security
- **Passlib[argon2] 1.7.4+**: Password hashing with Argon2id
- **Python-JOSE[cryptography] 3.5.0+**: JWT token generation and validation
- **Cryptography 46.0.2+**: Fernet encryption for sensitive fields

### Development Tools
- **UV**: Modern Python package manager (replaces pip/poetry)
- **Ruff 0.14.0+**: Fast linter and formatter (replaces Black/Flake8/isort)
- **Pre-commit 4.3.0+**: Git hooks for automated code quality checks
- **Pytest 8.4.2+**: Testing framework
- **Loguru 0.7.3+**: Enhanced logging with better formatting

### Additional Libraries
- **Requests 2.32.5+**: HTTP client for external APIs
- **Decimal**: Precise financial calculations (built-in)

---

## Architecture

### Design Pattern: Layered Architecture (3-Tier)

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (Routers)                          │
│  - FastAPI route handlers                              │
│  - Request/response validation (Pydantic schemas)      │
│  - Dependency injection                                │
├─────────────────────────────────────────────────────────┤
│  BUSINESS LOGIC LAYER (Managers + Services)            │
│  - CRUD operations (Managers)                          │
│  - Domain logic (Services)                             │
│  - Business rules and calculations                     │
├─────────────────────────────────────────────────────────┤
│  DATA ACCESS LAYER (Models + Database)                 │
│  - SQLAlchemy ORM models                               │
│  - Database queries                                    │
│  - Connection pooling                                  │
└─────────────────────────────────────────────────────────┘
```

### Key Design Patterns

#### 1. Repository Pattern (Managers)
- **Base Class**: `BaseCRUDManager` in `backend/managers/base_crud.py`
- **Purpose**: Abstract database operations, provide reusable CRUD methods
- **Example**:
```python
class UserManager(BaseCRUDManager):
    _model_class = User
    eager_load = ["wallets.addresses.chain", "portfolios"]

    async def get_user(self, username: str, session: AsyncSession) -> User:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
```

#### 2. Factory Pattern (Database)
- **Location**: `backend/databases/factory_async.py`
- **Purpose**: Create appropriate database instance based on configuration
- **Usage**: Abstracts database type selection (PostgreSQL/MariaDB)

#### 3. Dependency Injection
- **Framework**: FastAPI's built-in DI system
- **Pattern**: Use `Depends()` for all shared resources
- **Example**:
```python
async def get_user(
    username: str,
    user_manager: Annotated[UserManager, Depends(UserManager)],
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    return await user_manager.get_user(username, session)
```

#### 4. Singleton Pattern
- **Settings**: Cached with `@lru_cache` in `backend/settings.py`
- **Database Instance**: Single global instance `_db_instance`
- **Encryption Manager**: Class-level state management

#### 5. Active Record Pattern
- **Location**: `backend/databases/models/base.py`
- **Methods**: `save()`, `delete()`, `update()`, `to_dict()`
- **Example**:
```python
user = User(username="alice", email="alice@example.com")
await user.save(session)
```

#### 6. Strategy Pattern
- **Abstract Base**: `BaseAsyncDatabase`
- **Implementations**: `AsyncPostgresDatabase`, `AsyncMariaDBDatabase`
- **Purpose**: Support multiple database backends

#### 7. Decorator Pattern
- **EncryptedString**: Custom SQLAlchemy TypeDecorator for automatic encryption
- **Field Validators**: Pydantic validators for schema validation
- **Example**:
```python
class CexAccount(Base):
    api_key = Column(EncryptedString(500))  # Auto-encrypts on save
    api_secret = Column(EncryptedString(500))
```

### Dual ID Strategy

**Every model uses two identifiers:**
- **`id` (BigInteger)**: Internal use, database joins, foreign keys
- **`uuid` (UUID4)**: External use, API exposure, prevents enumeration attacks

**Rationale**: Prevents sequential ID guessing while maintaining efficient joins.

**Example**:
```python
# API returns UUID
GET /user/{username} → {"uuid": "550e8400-e29b-41d4-a716-446655440000", ...}

# Internal joins use id
SELECT * FROM wallets WHERE user_id = 123;  # Fast integer join
```

---

## Directory Structure

```
bagtracker/
├── backend/                          # Main application code
│   ├── __init__.py
│   ├── asgi.py                      # ASGI entry point (3 run modes)
│   ├── application.py               # FastAPI app factory
│   ├── dependencies.py              # Shared dependencies (auth, sessions)
│   ├── errors.py                    # Custom exception classes
│   ├── logger.py                    # Loguru configuration
│   ├── settings.py                  # Pydantic settings (50+ env vars)
│   ├── validators.py                # Custom validation utilities
│   │
│   ├── alembic/                     # Database migrations
│   │   ├── env.py                   # Alembic environment config
│   │   └── versions/                # Migration files
│   │
│   ├── databases/                   # Database layer
│   │   ├── base.py                  # Abstract base classes
│   │   ├── factory.py               # Sync database factory
│   │   ├── factory_async.py         # Async database factory
│   │   ├── postgres.py              # PostgreSQL implementation
│   │   ├── mariadb.py               # MariaDB support
│   │   ├── redis.py                 # Redis client
│   │   └── models/                  # SQLAlchemy ORM models
│   │       ├── base.py              # Base model with common fields
│   │       ├── balance.py           # Balance, BalanceHistory, Transaction
│   │       ├── chain.py             # Chain, Token, RPC
│   │       ├── portfolio.py         # User, Portfolio, CexAccount
│   │       └── wallet.py            # Wallet, WalletAddress
│   │
│   ├── managers/                    # Business logic (CRUD operations)
│   │   ├── base_crud.py             # Generic CRUD manager
│   │   ├── balance.py               # Balance CRUD
│   │   ├── portfolio.py             # Portfolio CRUD
│   │   ├── transactions.py          # Transaction CRUD
│   │   ├── users.py                 # User CRUD
│   │   └── wallets.py               # Wallet CRUD
│   │
│   ├── providers/                   # External service integrations
│   │   ├── eth.py                   # Ethereum RPC provider
│   │   └── tokens.py                # Token price providers (CoinGecko)
│   │
│   ├── routers/                     # API endpoints
│   │   ├── __init__.py              # Main router aggregator
│   │   ├── balance.py               # Balance endpoints
│   │   ├── healthcheck.py           # Health check endpoint
│   │   ├── portfolio.py             # Portfolio endpoints
│   │   ├── transactions.py          # Transaction endpoints
│   │   ├── users.py                 # User endpoints (sign-up, login)
│   │   └── wallets.py               # Wallet endpoints
│   │
│   ├── schemas/                     # Pydantic models (DTOs)
│   │   ├── base.py                  # Base response models
│   │   ├── balance.py               # Balance request/response schemas
│   │   ├── portfolio.py             # Portfolio schemas
│   │   ├── transactions.py          # Transaction schemas
│   │   ├── users.py                 # User schemas (signup, login)
│   │   └── wallets.py               # Wallet schemas
│   │
│   ├── security/                    # Security utilities
│   │   ├── encryption.py            # Fernet encryption manager
│   │   ├── jwt.py                   # JWT token handling
│   │   └── password.py              # Argon2 password hashing
│   │
│   ├── services/                    # Domain services
│   │   └── balance_calculator.py   # FIFO cost basis calculation
│   │
│   └── seeds/                       # Database seeders
│       ├── seed.py                  # Seeder CLI
│       └── data/                    # Seed data files (JSON/Python)
│           └── chains.py            # Chain seed data
│
├── docker/                          # Docker configuration
│   ├── Dockerfile                   # Production image
│   └── Dockerfile.dev               # Development image
│
├── scripts/                         # Utility scripts
│   ├── extract_version.py           # Extract version from pyproject.toml
│   ├── generate_encryption_key.py   # Generate Fernet keys
│   ├── rotate_encryption_keys.py    # Rotate encryption keys
│   ├── update_openapi_assets.py     # Update Swagger/ReDoc assets
│   └── verify_uvicorn_config.py     # Validate uvicorn config
│
├── static/                          # Static assets
│   └── openapi/                     # Self-hosted OpenAPI UI assets
│       ├── favicon.png
│       ├── redoc.standalone.js
│       ├── swagger-ui-bundle.js
│       └── swagger-ui.css
│
├── tests/                           # Test files (currently empty)
│   └── __init__.py
│
├── .dockerignore                    # Docker build exclusions
├── .gitignore                       # Git exclusions
├── .pre-commit-config.yaml          # Pre-commit hooks (ruff)
├── .python-version                  # Python version (3.12)
├── alembic.ini                      # Alembic configuration
├── docker-compose.yml               # Docker services (app, db, redis)
├── pyproject.toml                   # Project metadata, dependencies, ruff config
├── README.md                        # User documentation
├── sample.env                       # Environment variable template
├── uv.lock                          # UV lockfile
└── uvicorn_config.py                # Production Uvicorn config
```

### Key Directory Purposes

- **`backend/databases/models/`**: Database schema definitions (source of truth)
- **`backend/managers/`**: Business logic and CRUD operations
- **`backend/routers/`**: API endpoint definitions
- **`backend/schemas/`**: API request/response validation
- **`backend/services/`**: Complex domain logic (e.g., balance calculations)
- **`backend/providers/`**: External service integrations (Web3, price APIs)
- **`backend/security/`**: Authentication, encryption, password hashing

---

## Database Design

### Database Technology
- **Production**: PostgreSQL 14+ with asyncpg driver
- **TimescaleDB**: Time-series extension for PostgreSQL (hypertables for balance history)
- **ORM**: SQLAlchemy 2.0+ (async-first)
- **Migrations**: Alembic with auto-generation
- **Caching**: Redis for session storage and performance

**IMPORTANT**: This project requires PostgreSQL with TimescaleDB extension. SQLite is **NOT** supported due to:
- TimescaleDB hypertables with composite primary keys
- PostgreSQL-specific functions (`gen_random_uuid()`)
- PostgreSQL regex operators (`~` for CHECK constraints)
- Partial indexes with `WHERE` clauses
- `BIGINT PRIMARY KEY` with autoincrement in specific configurations

### Connection Management
- **Pooling**: `AsyncAdaptedQueuePool` with configurable size
- **Pool Size**: 10 connections (base) + 20 overflow
- **Session Lifecycle**: Request-scoped via FastAPI dependency injection

### Core Models

#### User Model (`backend/databases/models/portfolio.py`)
```python
class User(Base):
    __tablename__ = "users"

    # Dual ID strategy
    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    # Authentication
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Relationships
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user")

    # Soft delete
    is_deleted = Column(Boolean, default=False)
```

**Key Features**:
- Soft delete support
- Unique constraints with partial indexes (ignores deleted records)
- Argon2id password hashing
- One-to-many with wallets and portfolios

#### Wallet Model (`backend/databases/models/wallet.py`)
```python
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    wallet_type = Column(Enum(WalletType), nullable=False)  # metamask, tronlink, leather
    sync_enabled = Column(Boolean, default=True)
    total_value_usd = Column(Numeric(38, 18), default=0)

    # Relationships
    user = relationship("User", back_populates="wallets")
    addresses = relationship("WalletAddress", back_populates="wallet", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="wallet")
    balances = relationship("Balance", back_populates="wallet")
```

**Multi-Chain Support**: Wallets can have multiple addresses across different chains via `WalletAddress`.

#### WalletAddress Model
```python
class WalletAddress(Base):
    __tablename__ = "wallet_addresses"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    wallet_id = Column(BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"))
    chain_id = Column(BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"))

    address = Column(String(100), nullable=False)
    address_lowercase = Column(String(100), nullable=False, index=True)

    last_sync_at = Column(DateTime(timezone=True))
    last_sync_block = Column(BigInteger)

    # Unique constraint per wallet-chain and address-chain
    __table_args__ = (
        UniqueConstraint("wallet_id", "chain_id"),
        UniqueConstraint("address_lowercase", "chain_id"),
    )
```

**Design**: Junction table for many-to-many between Wallet and Chain, with sync tracking.

#### Chain Model (`backend/databases/models/chain.py`)
```python
class Chain(Base):
    __tablename__ = "chains"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    chain_id = Column(BigInteger, unique=True, nullable=False)  # e.g., 1 for Ethereum
    name = Column(String(50), unique=True, nullable=False)
    short_name = Column(String(10), nullable=False)
    chain_type = Column(String(20), default="evm")  # evm, tron, solana, stacks

    explorer_url = Column(String(200))
    is_testnet = Column(Boolean, default=False)

    # Relationships
    tokens = relationship("Token", back_populates="chain")
    wallet_addresses = relationship("WalletAddress", back_populates="chain")
```

**Supported Chains**: Ethereum, BSC, Polygon, Arbitrum, Tron, Solana, Stacks (extensible).

#### Token Model
```python
class Token(Base):
    __tablename__ = "tokens"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    chain_id = Column(BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"))

    contract_address = Column(String(100))
    contract_address_lowercase = Column(String(100), index=True)

    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    decimals = Column(SmallInteger, default=18)  # 0-18

    is_native = Column(Boolean, default=False)  # ETH, BNB, MATIC, etc.
    coingecko_id = Column(String(100))
    current_price_usd = Column(Numeric(38, 18))

    __table_args__ = (
        UniqueConstraint("contract_address_lowercase", "chain_id"),
    )
```

**Price Tracking**: CoinGecko integration for real-time USD prices.

#### Transaction Model (`backend/databases/models/balance.py`)
```python
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    wallet_id = Column(BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"))
    token_id = Column(BigInteger, ForeignKey("tokens.id", ondelete="RESTRICT"))
    chain_id = Column(BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"))

    transaction_type = Column(Enum(TransactionType), nullable=False)
    # BUY, SELL, TRANSFER_IN, TRANSFER_OUT

    amount = Column(Numeric(38, 0), nullable=False)  # Raw amount (no decimals)
    amount_decimal = Column(Numeric(38, 18))  # Human-readable amount
    price_usd = Column(Numeric(38, 18))

    transaction_hash = Column(String(100), nullable=False)
    block_number = Column(BigInteger)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    gas_used = Column(Numeric(38, 0))
    gas_price = Column(Numeric(38, 0))

    is_cancelled = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("transaction_hash", "chain_id"),
    )
```

**Transaction Types**:
- `BUY`: Purchase tokens (increases balance, sets cost basis)
- `SELL`: Sell tokens (decreases balance, realizes P&L)
- `TRANSFER_IN`: Receive tokens (increases balance)
- `TRANSFER_OUT`: Send tokens (decreases balance)

#### Balance Model
```python
class Balance(Base):
    __tablename__ = "balances"

    id = Column(BigInteger, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)

    wallet_id = Column(BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"))
    token_id = Column(BigInteger, ForeignKey("tokens.id", ondelete="RESTRICT"))
    chain_id = Column(BigInteger, ForeignKey("chains.id", ondelete="RESTRICT"))

    amount = Column(Numeric(38, 0), nullable=False)
    amount_decimal = Column(Numeric(38, 18), nullable=False)

    avg_buy_price_usd = Column(Numeric(38, 18))  # FIFO cost basis
    avg_sell_price_usd = Column(Numeric(38, 18))

    total_buy_value_usd = Column(Numeric(38, 18))
    total_sell_value_usd = Column(Numeric(38, 18))

    value_usd = Column(Numeric(38, 18))  # Current market value
    unrealized_pnl_usd = Column(Numeric(38, 18))

    change_24h = Column(Numeric(10, 2))
    change_24h_percent = Column(Numeric(10, 2))

    __table_args__ = (
        UniqueConstraint("wallet_id", "token_id", "chain_id"),
        CheckConstraint("amount >= 0", name="check_balance_amount_positive"),
    )
```

**FIFO Cost Basis**: Calculated by `BalanceCalculatorService` in `backend/services/balance_calculator.py`.

#### BalanceHistory Model (TimescaleDB Hypertable)
```python
class BalanceHistory(Base, BalanceBase):
    __tablename__ = "balances_history"

    # Composite primary key required for TimescaleDB hypertable
    # snapshot_date MUST be first for time-series partitioning
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="hourly"
    )  # transaction, hourly, daily, weekly, monthly

    triggered_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # transaction, price_change, scheduled

    # Relationships
    token = relationship("Token", back_populates="balances_history")
    wallet = relationship("Wallet", back_populates="balances_history")
    chain = relationship("Chain", back_populates="balances_history")

    __table_args__ = (
        # CRITICAL: Composite primary key for TimescaleDB hypertable
        # snapshot_date must be first for proper partitioning
        PrimaryKeyConstraint("snapshot_date", "id"),
        CheckConstraint(
            "snapshot_type IN ('transaction', 'hourly', 'daily', 'weekly', 'monthly')",
            name="valid_snapshot_type"
        ),
        Index("ix_balance_history_token_date", "token_id", "chain_id", "snapshot_date"),
        Index("ix_balance_history_type_date", "snapshot_type", "snapshot_date"),
        Index("ix_balance_history_wallet_date", "wallet_id", "snapshot_date"),
    )
```

**TimescaleDB Hypertable**: This table is converted to a TimescaleDB hypertable partitioned by `snapshot_date`. The composite primary key `(snapshot_date, id)` is **required** for hypertable functionality. Inherits balance fields from `BalanceBase` mixin.

**CRITICAL**: Do NOT change the primary key structure. SQLite cannot support this table structure.

### Database Conventions

#### Naming
- **Tables**: Plural snake_case (`users`, `wallet_addresses`, `balance_history`)
- **Columns**: Snake_case (`created_at`, `avg_buy_price_usd`, `is_deleted`)
- **Indexes**: Prefixed (`ix_`, `idx_`, `uq_`)
- **Foreign Keys**: `{table_singular}_id` (`user_id`, `wallet_id`, `chain_id`)

#### Common Fields (All Models)
```python
id = Column(BigInteger, primary_key=True)
uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
updated_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
is_deleted = Column(Boolean, default=False)
```

#### Numeric Precision
- **Balances**: `Numeric(38, 0)` for raw amounts, `Numeric(38, 18)` for decimal amounts
- **Prices**: `Numeric(38, 18)` for USD values
- **Rationale**: Handles tokens with up to 18 decimals (Ethereum standard)

#### Soft Delete
- All user-facing models have `is_deleted` flag
- Deleted records excluded from queries via default filters
- Unique constraints use partial indexes: `where="is_deleted = false"`

#### Encryption
```python
from backend.security.encryption import EncryptedString

class CexAccount(Base):
    api_key = Column(EncryptedString(500))  # Auto-encrypts with Fernet
    api_secret = Column(EncryptedString(500))
```

**Encrypted Fields**: API keys, secrets, private keys (automatic encryption/decryption).

### TimescaleDB Hypertables

BagTracker uses TimescaleDB for efficient time-series data storage. Three tables are configured as hypertables:

#### 1. BalanceHistory (`balances_history`)
```python
class BalanceHistory(Base, BalanceBase):
    __tablename__ = "balances_history"

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_date", "id"),  # Composite PK required
        # ... other constraints
    )
```
- **Partitioned by**: `snapshot_date`
- **Purpose**: Track wallet balance changes over time
- **Snapshot types**: transaction, hourly, daily, weekly, monthly
- **Inherits from**: `BalanceBase` mixin (wallet_id, token_id, chain_id, amounts, prices)

#### 2. NFTBalanceHistory (`nft_balances_history`)
```python
class NFTBalanceHistory(Base, NFTBalanceBase):
    __tablename__ = "nft_balances_history"

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_date", "id"),  # Composite PK required
        # ... other constraints
    )
```
- **Partitioned by**: `snapshot_date`
- **Purpose**: Track NFT balance changes over time
- **Inherits from**: `NFTBalanceBase` mixin (wallet_id, contract_address, nft_token_id, metadata)

#### 3. CexBalanceHistory (`cex_balances_history`)
```python
class CexBalanceHistory(Base, CexBalanceBase):
    __tablename__ = "cex_balances_history"

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_date", "id"),  # Composite PK required
        # ... other constraints
    )
```
- **Partitioned by**: `snapshot_date`
- **Purpose**: Track CEX (centralized exchange) balance changes over time
- **Inherits from**: `CexBalanceBase` mixin (subaccount_id, token_id, amounts, prices, asset_type)

#### Hypertable Creation

Hypertables are created in the initial migration (`backend/alembic/versions/b1423ae03e75_init_migration.py`):

```python
def upgrade() -> None:
    # ... create tables ...

    # Convert to hypertables
    op.execute("SELECT create_hypertable('balances_history', 'snapshot_date', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('nft_balances_history', 'snapshot_date', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('cex_balances_history', 'snapshot_date', if_not_exists => TRUE)")
```

#### Critical Requirements

**⚠️ IMPORTANT: Composite Primary Key Order**

All hypertable models MUST have a composite primary key with **`snapshot_date` FIRST**:
```python
PrimaryKeyConstraint("snapshot_date", "id")  # ✅ CORRECT
PrimaryKeyConstraint("id", "snapshot_date")  # ❌ WRONG - breaks partitioning
```

The time-based column (`snapshot_date`) must be the first column in the composite primary key for TimescaleDB to properly partition the data.

**Why Composite PKs?**
- TimescaleDB hypertables require the partitioning column in the primary key
- The `id` column provides uniqueness within each time partition
- This allows efficient time-based queries while maintaining row uniqueness

**SQLite Incompatibility**
These tables **cannot** be used with SQLite because:
- SQLite doesn't support TimescaleDB extensions
- Composite primary keys with autoincrement columns have limitations
- PostgreSQL-specific server defaults (`func.now()`, `func.gen_random_uuid()`)

**Testing**: Always use PostgreSQL (preferably in a Docker container) for testing. Never attempt to run these models with SQLite.

### Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "Add CEX account support"

# Review generated migration in backend/alembic/versions/
# Edit if needed (Alembic doesn't detect everything)

# Apply migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Check current version
alembic current

# View migration history
alembic history
```

**Important**: Always review auto-generated migrations before applying!

---

## API Design

### Routing Structure

All routes aggregated in `backend/routers/__init__.py`:
```python
from fastapi import APIRouter
from . import healthcheck, users, wallets, transactions, balance, portfolio

main_router = APIRouter(dependencies=common)
main_router.include_router(healthcheck.router, tags=['Health check'])
main_router.include_router(users.router, tags=['Users'])
main_router.include_router(wallets.router, tags=['Wallets'])
main_router.include_router(transactions.router, tags=['Transactions'])
main_router.include_router(balance.router, tags=['Balance'])
main_router.include_router(portfolio.router, tags=['Portfolio'])
```

### RESTful Conventions

#### Standard CRUD Operations
```python
# Users (backend/routers/users.py)
POST   /sign-up              # Create user
POST   /log-in               # Authenticate user
GET    /user/{username}      # Get user by username
PUT    /user/{username}      # Full update
PATCH  /user/{username}      # Partial update
DELETE /user/{username}      # Soft delete user

# Wallets (backend/routers/wallets.py)
POST   /wallet               # Create wallet
GET    /wallet/{wallet_uuid} # Get wallet by UUID
GET    /user/wallets/{username}  # List user's wallets
PUT    /wallet/{wallet_uuid} # Update wallet
DELETE /wallet/{wallet_uuid} # Delete wallet

# Transactions (backend/routers/transactions.py)
POST   /transaction          # Create transaction
GET    /transaction/{transaction_uuid}  # Get transaction
GET    /wallet/transactions/{wallet_uuid}  # List wallet transactions
POST   /transaction/cancel/{transaction_id}  # Cancel transaction (action endpoint)

# Balance (backend/routers/balance.py)
GET    /balance/wallet/{wallet_uuid}  # Get wallet balances
GET    /balance/user/{username}       # Get all user balances
POST   /balance/recalculate/wallet/{wallet_id}  # Recalculate (admin)
GET    /balance/history/{balance_uuid}  # Get balance history
```

### Request/Response Patterns

#### Request Validation (Pydantic Schemas)
```python
# backend/schemas/users.py
class UserSignUp(BaseModel):
    username: str
    password: str
    email: EmailStr

    @field_validator("username")
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v.lower()

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

#### Response Models
```python
# backend/schemas/users.py
class UserResponse(BaseModel):
    uuid: UUID
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()
```

#### Endpoint Definition
```python
# backend/routers/users.py
@router.post("/sign-up", response_model=UserResponse, status_code=201)
async def sign_up(
    user_data: UserSignUp,
    user_manager: Annotated[UserManager, Depends(UserManager)],
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> User:
    """
    Create a new user account.

    - **username**: Unique username (3-50 chars, alphanumeric)
    - **password**: Password (min 8 chars)
    - **email**: Valid email address
    """
    # Check if user exists
    existing = await user_manager.get_user(user_data.username, session)
    if existing:
        raise BadRequestException("Username already exists")

    # Create user
    user = User(
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        password_hash=hash_password(user_data.password)
    )
    await user.save(session)
    return user
```

### Error Handling

#### Custom Exceptions (`backend/errors.py`)
```python
class GeneralProcessingException(Exception):
    message = "Unknown backend problem"
    status_code = 500

class BadRequestException(GeneralProcessingException):
    status_code = 400

class UserError(GeneralProcessingException):
    status_code = 404
    message = "User not found"

class WalletError(GeneralProcessingException):
    status_code = 404
    message = "Wallet not found"
```

#### Global Exception Handler (`backend/application.py`)
```python
@app.exception_handler(GeneralProcessingException)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": exc.__class__.__name__,
            "message": exc.message
        }
    )
```

#### Usage in Endpoints
```python
@router.get("/user/{username}")
async def get_user(username: str, ...):
    user = await user_manager.get_user(username, session)
    if not user or user.is_deleted:
        raise UserError()  # Returns 404 with {"type": "UserError", "message": "User not found"}
    return user
```

### Authentication

#### Token-Based Auth (`backend/dependencies.py`)
```python
class TokenAuth(HTTPBearer):
    def __init__(self, name: str = "X-Auth-Token"):
        super().__init__(auto_error=False)
        self.name = name

    async def __call__(self, request: Request):
        token = request.headers.get(self.name)
        if not token:
            raise HTTPException(status_code=403, detail="Not authorized")
        # Validate token...
        return token

# Apply to specific endpoints
token_auth = [Depends(TokenAuth(name=settings.token_header_name))]

@router.post("/admin/action", dependencies=token_auth)
async def admin_action(...):
    pass  # Only accessible with valid X-Auth-Token header
```

### API Documentation

#### Swagger UI: `http://localhost:8080/docs`
- Interactive API testing
- Auto-generated from endpoint definitions
- Self-hosted assets (no CDN dependency)

#### ReDoc: `http://localhost:8080/redoc`
- Alternative documentation UI
- Better for reading/documentation sharing

#### OpenAPI JSON: `http://localhost:8080/openapi.json`
- Machine-readable API specification

#### Customization (`backend/application.py`)
```python
app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"url": "/openapi.json"}
)
```

### Status Codes

- **200 OK**: Successful GET/PUT/PATCH
- **201 Created**: Successful POST (resource created)
- **204 No Content**: Successful DELETE
- **400 Bad Request**: Validation error, business rule violation
- **403 Forbidden**: Not authorized (missing/invalid token)
- **404 Not Found**: Resource doesn't exist
- **500 Internal Server Error**: Unexpected error

---

## Development Workflow

### Initial Setup

#### 1. Install UV Package Manager
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

#### 2. Clone and Setup Project
```bash
# Clone repository
git clone https://github.com/gearbox/bagtracker.git
cd bagtracker

# Create virtual environment
uv venv

# Install dependencies (production)
uv sync

# Install with dev tools (recommended for development)
uv sync --group dev

# Activate virtualenv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

#### 3. Configure Environment
```bash
# Copy sample environment file
cp sample.env .env

# Edit .env with your settings
# CRITICAL: Update these values
# - POSTGRES_PASSWORD
# - SECRET_KEY (for JWT)
# - ENCRYPTION_KEY (for sensitive data)
```

#### 4. Generate Encryption Key
```bash
python scripts/generate_encryption_key.py
# Copy output to .env ENCRYPTION_KEY variable
```

#### 5. Start Database (Docker)
```bash
docker-compose up -d db redis
```

#### 6. Run Migrations
```bash
alembic upgrade head
```

#### 7. Seed Initial Data
```bash
python -m backend.seeds.seed chains seed
```

#### 8. Run Application
```bash
# Development mode (auto-reload)
python -m uvicorn backend.asgi:app --reload --host 0.0.0.0 --port 8080

# Or using FastAPI CLI
fastapi run backend/asgi.py --proxy-headers --port 80

# Or direct Python
python -m backend.asgi
```

#### 9. Verify Installation
- Visit: http://localhost:8080/docs
- Check health: http://localhost:8080/healthcheck

### Daily Development

#### Running the Application
```bash
# Activate virtualenv
source .venv/bin/activate

# Start application (auto-reload)
python -m uvicorn backend.asgi:app --reload --host 0.0.0.0 --port 8080
```

#### Code Quality
```bash
# Format code
ruff format

# Lint and auto-fix
ruff check --fix

# Or use pre-commit (auto-runs on commit)
pre-commit install  # One-time setup
git commit -m "message"  # Auto-runs ruff
```

#### Database Migrations
```bash
# Make changes to models in backend/databases/models/

# Generate migration
alembic revision --autogenerate -m "Add user avatar field"

# Review generated migration
# Edit backend/alembic/versions/XXXXX_add_user_avatar_field.py if needed

# Apply migration
alembic upgrade head

# If something went wrong, rollback
alembic downgrade -1
```

#### Testing
```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=backend

# Run specific test
pytest tests/test_users.py::test_user_creation
```

### Docker Workflow

#### Start All Services
```bash
# Build and start
docker-compose up --build

# Or in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f app-backend
```

#### Execute Commands in Container
```bash
# Run migrations
docker-compose exec app-backend alembic upgrade head

# Seed data
docker-compose exec app-backend python -m backend.seeds.seed chains seed

# Open Python shell
docker-compose exec app-backend python

# Open bash
docker-compose exec app-backend bash
```

#### Stop Services
```bash
docker-compose down

# Remove volumes (WARNING: deletes database data)
docker-compose down -v
```

### Common Development Tasks

#### Add New API Endpoint

**Step 1: Create Pydantic Schema** (`backend/schemas/feature.py`)
```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class FeatureCreate(BaseModel):
    name: str
    description: str | None = None

class FeatureResponse(BaseModel):
    uuid: UUID
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
```

**Step 2: Add Route** (`backend/routers/feature.py`)
```python
from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from backend.dependencies import get_async_session
from backend.managers.feature import FeatureManager
from backend.schemas.feature import FeatureCreate, FeatureResponse

router = APIRouter(prefix="/feature")

@router.post("", response_model=FeatureResponse, status_code=201)
async def create_feature(
    data: FeatureCreate,
    manager: Annotated[FeatureManager, Depends(FeatureManager)],
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    feature = await manager.create(data, session)
    return feature
```

**Step 3: Include Router** (`backend/routers/__init__.py`)
```python
from . import feature
main_router.include_router(feature.router, tags=['Features'])
```

**Step 4: Test**
- Visit http://localhost:8080/docs
- Test endpoint in Swagger UI

#### Add New Database Model

**Step 1: Define Model** (`backend/databases/models/feature.py`)
```python
from sqlalchemy import Column, String, Text, BigInteger
from .base import Base

class Feature(Base):
    __tablename__ = "features"

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
```

**Step 2: Import Model** (`backend/databases/models/__init__.py`)
```python
from .feature import Feature
```

**Step 3: Create Migration**
```bash
alembic revision --autogenerate -m "Add feature model"
```

**Step 4: Review and Apply**
```bash
# Review: backend/alembic/versions/XXXXX_add_feature_model.py
alembic upgrade head
```

#### Add New Manager

**Create Manager** (`backend/managers/feature.py`)
```python
from backend.managers.base_crud import BaseCRUDManager
from backend.databases.models.feature import Feature

class FeatureManager(BaseCRUDManager):
    _model_class = Feature
    eager_load = []  # Add relationships to eager load

    # Add custom methods
    async def get_by_name(self, name: str, session):
        result = await session.execute(
            select(Feature).where(Feature.name == name)
        )
        return result.scalar_one_or_none()
```

#### Update OpenAPI Assets
```bash
# Update to latest versions
python scripts/update_openapi_assets.py

# Update to specific versions
python scripts/update_openapi_assets.py --swagger-version 5.10.0 --redoc-version 2.1.0
```

#### Rotate Encryption Keys
```bash
# Generate new key
python scripts/generate_encryption_key.py

# Add new key to .env as ENCRYPTION_KEY
# Move old key to ENCRYPTION_KEY_OLD

# Rotate all encrypted data
python scripts/rotate_encryption_keys.py
```

---

## Code Conventions

### Python Style

#### Linter/Formatter: Ruff
Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 120
indent-width = 4

[tool.ruff.format]
quote-style = "double"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "SIM", "UP"]
ignore = ["UP046", "B008"]
```

**Commands**:
```bash
ruff check --fix    # Lint and auto-fix
ruff format         # Format code
```

#### Naming Conventions

**Files**: `snake_case.py`
```
base_crud.py
balance_calculator.py
```

**Classes**: `PascalCase`
```python
class UserManager:
class BalanceCalculator:
class WalletResponse:
```

**Functions/Methods**: `snake_case`
```python
def get_user():
async def create_wallet():
def calculate_balance():
```

**Variables**: `snake_case`
```python
user_manager = UserManager()
wallet_id = 123
balance_value_usd = Decimal("100.50")
```

**Constants**: `UPPER_CASE`
```python
MAX_USERNAME_LENGTH = 50
DEFAULT_DECIMALS = 18
```

**Private Members**: Prefix with `_`
```python
class Example:
    _model_class = User
    _internal_state = {}

    def _helper_method(self):
        pass
```

#### Type Hints

**Always use type hints**:
```python
# Good
async def get_user(username: str, session: AsyncSession) -> User | None:
    pass

# Bad
async def get_user(username, session):
    pass
```

**Use modern syntax** (Python 3.10+):
```python
# Good
def process(data: str | None) -> list[dict[str, Any]]:
    pass

# Old style (avoid)
from typing import Optional, List, Dict
def process(data: Optional[str]) -> List[Dict[str, Any]]:
    pass
```

**FastAPI Dependency Injection**:
```python
from typing import Annotated
from fastapi import Depends

async def handler(
    user_manager: Annotated[UserManager, Depends(UserManager)],
    session: Annotated[AsyncSession, Depends(get_async_session)]
):
    pass
```

#### Async/Await

**All database operations are async**:
```python
# Good
async def get_user(username: str, session: AsyncSession):
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

# Bad (sync in async context)
def get_user(username: str, session: Session):
    return session.query(User).filter_by(username=username).first()
```

**Router handlers are async**:
```python
@router.get("/user/{username}")
async def get_user(username: str, ...):
    user = await user_manager.get_user(username, session)
    return user
```

#### Docstrings

**Use for complex logic**:
```python
async def calculate_fifo_cost_basis(transactions: list[Transaction]) -> Decimal:
    """
    Calculate FIFO (First In, First Out) cost basis from transaction history.

    Args:
        transactions: List of transactions sorted by timestamp ascending

    Returns:
        Decimal: Average cost basis per token

    Raises:
        ValueError: If transactions list is empty
    """
    pass
```

**API endpoints include description**:
```python
@router.post("/sign-up", response_model=UserResponse, status_code=201)
async def sign_up(user_data: UserSignUp, ...):
    """
    Create a new user account.

    - **username**: Unique username (3-50 chars, alphanumeric)
    - **password**: Password (min 8 chars)
    - **email**: Valid email address
    """
    pass
```

### Import Organization

**Order** (enforced by Ruff):
1. Standard library
2. Third-party packages
3. Local application imports

```python
# Standard library
import os
from datetime import datetime
from typing import Annotated

# Third-party
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from backend.dependencies import get_async_session
from backend.managers.users import UserManager
from backend.schemas.users import UserResponse
```

### Error Handling

#### Use Custom Exceptions
```python
from backend.errors import UserError, BadRequestException

# Good
if not user:
    raise UserError()

# Bad
if not user:
    raise HTTPException(status_code=404, detail="User not found")
```

#### Log Errors
```python
from loguru import logger
import traceback

try:
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    logger.error(traceback.format_exc())
    raise GeneralProcessingException()
```

### Logging

**Use Loguru**:
```python
from loguru import logger

# Info
logger.info("User created successfully")
logger.info(f"Processing wallet {wallet.uuid}")

# Warning
logger.warning(f"User {username} attempted invalid operation")

# Error
logger.error(f"Failed to sync wallet {wallet_id}: {error}")
logger.error(traceback.format_exc())

# Debug
logger.debug(f"Transaction data: {transaction_data}")
```

### Database Queries

#### Use SQLAlchemy 2.0 Syntax
```python
from sqlalchemy import select

# Good (2.0 style)
async def get_user(username: str, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()

# Bad (1.x legacy style)
async def get_user(username: str, session: AsyncSession):
    return await session.query(User).filter_by(username=username).first()
```

#### Eager Loading
```python
from sqlalchemy.orm import selectinload

# Load user with wallets and addresses
stmt = select(User).options(
    selectinload(User.wallets).selectinload(Wallet.addresses)
).where(User.username == username)

result = await session.execute(stmt)
user = result.scalar_one_or_none()
```

#### Use Managers for CRUD
```python
# Good
user = await user_manager.get_user(username, session)

# Avoid (unless necessary)
result = await session.execute(select(User).where(...))
user = result.scalar_one_or_none()
```

---

## Security Practices

### Password Hashing

**Algorithm**: Argon2id (industry standard)

**Location**: `backend/security/password.py`

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain, hashed)
```

**Usage**:
```python
# Sign up
user = User(
    username=data.username,
    password_hash=hash_password(data.password)
)

# Login
if not verify_password(password, user.password_hash):
    raise BadRequestException("Invalid credentials")
```

### Data Encryption

**Algorithm**: Fernet (symmetric encryption)

**Location**: `backend/security/encryption.py`

**Use Cases**: API keys, secrets, private keys

**Configuration** (`.env`):
```bash
ENCRYPTION_KEY="your-fernet-key-here"
ENCRYPTION_KEY_OLD="old-key-for-rotation"  # Optional
```

**Generate Key**:
```bash
python scripts/generate_encryption_key.py
```

**Usage in Models**:
```python
from backend.security.encryption import EncryptedString

class CexAccount(Base):
    api_key = Column(EncryptedString(500))  # Automatically encrypted
    api_secret = Column(EncryptedString(500))
```

**Direct Usage**:
```python
from backend.security.encryption import EncryptionManager

manager = EncryptionManager(encryption_key)
encrypted = manager.encrypt("sensitive-data")
decrypted = manager.decrypt(encrypted)
```

**Key Rotation**:
```bash
# 1. Generate new key
python scripts/generate_encryption_key.py

# 2. Update .env
ENCRYPTION_KEY="new-key"
ENCRYPTION_KEY_OLD="old-key"

# 3. Rotate all encrypted data
python scripts/rotate_encryption_keys.py
```

### JWT Tokens

**Location**: `backend/security/jwt.py`

**Configuration** (`.env`):
```bash
SECRET_KEY="your-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Usage**:
```python
from backend.security.jwt import create_access_token, verify_token

# Create token
token = create_access_token(data={"sub": user.username})

# Verify token
payload = verify_token(token)
username = payload.get("sub")
```

### Dual ID Strategy (Enumeration Attack Prevention)

**Problem**: Sequential IDs allow enumeration attacks
```
GET /user/1    → User exists
GET /user/2    → User exists
GET /user/999  → Guess how many users exist
```

**Solution**: Expose UUIDs externally, use integer IDs internally
```python
class User(Base):
    id = Column(BigInteger, primary_key=True)  # Internal (joins, FKs)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid4)  # External (API)
```

**API Usage**:
```python
# API exposes UUIDs
GET /user/{username} → {"uuid": "550e8400-...", "username": "alice"}
GET /wallet/550e8400-e29b-41d4-a716-446655440000

# Database uses integer IDs
SELECT * FROM wallets WHERE user_id = 123;  # Fast join
```

### SQL Injection Prevention

**All queries use parameterized statements**:
```python
# Good (SQLAlchemy automatically parameterizes)
stmt = select(User).where(User.username == username)

# Bad (never build SQL strings manually)
query = f"SELECT * FROM users WHERE username = '{username}'"  # VULNERABLE!
```

### XSS Prevention

**Pydantic validates all inputs**:
```python
class UserSignUp(BaseModel):
    username: str  # Validated by Pydantic
    email: EmailStr  # Built-in email validation
```

**FastAPI auto-escapes responses**:
- JSON responses are safe by default
- HTML rendering not used in this API

### CORS (Cross-Origin Resource Sharing)

**Configuration** (`backend/application.py`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production**: Restrict `allow_origins` to specific domains!

### Secrets Management

**Never commit secrets to git**:
- `.env` is in `.gitignore`
- Use `sample.env` as template
- Use environment variables in production

**Required Secrets**:
```bash
SECRET_KEY=               # For JWT signing
ENCRYPTION_KEY=           # For data encryption
POSTGRES_PASSWORD=        # Database password
INFURA_API_KEY=          # Web3 provider
```

### Rate Limiting

**Current Status**: Not implemented

**Recommendation**: Add rate limiting for production
```python
# Example with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/endpoint")
@limiter.limit("10/minute")
async def endpoint():
    pass
```

---

## Common Tasks

### Create a New User

```bash
curl -X POST http://localhost:8080/sign-up \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "securepass123",
    "email": "alice@example.com"
  }'
```

### Create a Wallet

```bash
curl -X POST http://localhost:8080/wallet \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "wallet_type": "metamask",
    "addresses": [
      {
        "chain_id": 1,
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
      }
    ]
  }'
```

### Add a Transaction

```bash
curl -X POST http://localhost:8080/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": 1,
    "token_id": 1,
    "chain_id": 1,
    "transaction_type": "BUY",
    "amount": "1000000000000000000",
    "amount_decimal": "1.0",
    "price_usd": "2000.50",
    "transaction_hash": "0xabc123...",
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

### Query Balance

```bash
curl http://localhost:8080/balance/wallet/{wallet_uuid}
```

### Seed Chains

```bash
python -m backend.seeds.seed chains seed
```

### Backup Database

```bash
# Using Docker
docker-compose exec db pg_dump -U postgres portfolio > backup.sql

# Restore
docker-compose exec -T db psql -U postgres portfolio < backup.sql
```

### View Logs

```bash
# Application logs
docker-compose logs -f app-backend

# Database logs
docker-compose logs -f db

# All services
docker-compose logs -f
```

---

## Testing Guidelines

### Current Status
- **Test Framework**: pytest 8.4.2+
- **Coverage**: Minimal (needs improvement)
- **Location**: `/tests/` directory

### Running Tests (when implemented)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_users.py

# Run specific test
pytest tests/test_users.py::test_create_user

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Structure (Recommended)

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_models/
│   ├── test_user.py
│   ├── test_wallet.py
│   └── test_balance.py
├── test_managers/
│   ├── test_user_manager.py
│   └── test_wallet_manager.py
├── test_routers/
│   ├── test_users.py
│   └── test_wallets.py
└── test_services/
    └── test_balance_calculator.py
```

### Example Test (Recommended Pattern)

**IMPORTANT**: Tests MUST use PostgreSQL, not SQLite. The project uses TimescaleDB hypertables and PostgreSQL-specific features.

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.databases.models.base import Base

# Option 1: Use test PostgreSQL database
@pytest.fixture
async def async_session():
    # Use PostgreSQL test database
    TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/bagtracker_test"
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

    # Cleanup: drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

# Option 2: Use Docker container for tests (recommended)
# Start PostgreSQL container before running tests:
# docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=bagtracker_test timescale/timescaledb:latest-pg14
# Then use: postgresql+asyncpg://postgres:testpass@localhost:5433/bagtracker_test

# tests/test_managers/test_user_manager.py
import pytest
from backend.managers.users import UserManager
from backend.databases.models.portfolio import User

@pytest.mark.asyncio
async def test_create_user(async_session):
    manager = UserManager()

    user = User(username="testuser", email="test@example.com", password_hash="hash")
    await user.save(async_session)

    retrieved = await manager.get_user("testuser", async_session)
    assert retrieved.username == "testuser"
```

**Why PostgreSQL for Tests?**
- TimescaleDB hypertables (BalanceHistory, NFTBalanceHistory, CexBalanceHistory) require PostgreSQL
- PostgreSQL-specific functions: `gen_random_uuid()`, regex operators (`~`)
- Partial indexes with `WHERE` clauses
- Composite primary keys with autoincrement in hypertables

### Testing Best Practices

1. **Use PostgreSQL**: ALWAYS use PostgreSQL for tests, NEVER SQLite (see reasons above)
2. **Use Docker**: Run PostgreSQL in Docker container for consistent test environment
3. **Use fixtures** for common setup (database, users, wallets)
4. **Test isolation**: Each test should be independent
5. **Mock external services**: Don't call real Web3 providers, price APIs
6. **Test error cases**: Not just happy paths
7. **Use factories**: Create test data with factories (factory_boy)
8. **Async tests**: Mark with `@pytest.mark.asyncio`
9. **TimescaleDB**: If testing hypertable models, ensure TimescaleDB extension is enabled

---

## AI Assistant Guidelines

### Understanding This Codebase

**Key Characteristics**:
1. **Production-ready architecture**: Not a tutorial project
2. **Async-first**: All database operations use async/await
3. **Type-safe**: Extensive type hints throughout
4. **Financial precision**: Uses Decimal for monetary calculations
5. **Security-conscious**: Encryption, hashing, dual ID strategy
6. **Multi-chain**: Supports both EVM and non-EVM blockchains

### Making Changes

#### Before Modifying Code

1. **Read relevant files first**:
   - Model definitions in `backend/databases/models/`
   - Manager logic in `backend/managers/`
   - API contracts in `backend/schemas/`

2. **Check dependencies**:
   - Foreign key relationships
   - Existing managers that might be affected
   - API endpoints that use the model

3. **Understand data flow**:
   ```
   Request → Router → Manager → Database Model
   Response ← Schema ← Manager ← Query Result
   ```

#### When Adding Features

1. **Database changes**:
   - Update model in `backend/databases/models/`
   - Create migration with `alembic revision --autogenerate`
   - Review generated migration (Alembic misses some things)

2. **Business logic**:
   - Add methods to appropriate manager in `backend/managers/`
   - Use existing `BaseCRUDManager` methods when possible

3. **API**:
   - Create schemas in `backend/schemas/`
   - Add routes in `backend/routers/`
   - Include router in `backend/routers/__init__.py`

4. **Testing**:
   - Add tests for new functionality
   - Test both success and error cases

#### Common Pitfalls

**DON'T**:
- ❌ Use sync database operations (always async)
- ❌ Expose integer IDs in API (use UUIDs)
- ❌ Skip migrations (always create migrations for model changes)
- ❌ Hardcode secrets (use settings)
- ❌ Use `float` for money (use `Decimal`)
- ❌ Forget to review auto-generated migrations
- ❌ Add dependencies without updating `pyproject.toml`

**DO**:
- ✅ Use async/await for all database operations
- ✅ Use Pydantic for validation
- ✅ Follow existing naming conventions
- ✅ Add type hints to all functions
- ✅ Use managers for database operations
- ✅ Log errors with traceback
- ✅ Test changes in Swagger UI (`/docs`)

### Code Review Checklist

When reviewing or generating code, check:

- [ ] Type hints on all functions
- [ ] Async/await used correctly
- [ ] Pydantic schemas for request/response
- [ ] Custom exceptions for errors
- [ ] Logging for important operations
- [ ] Database queries use SQLAlchemy 2.0 syntax
- [ ] Migrations created for model changes
- [ ] UUIDs exposed in API, IDs used internally
- [ ] Decimal used for financial values
- [ ] Follows naming conventions (snake_case, PascalCase)
- [ ] Code formatted with ruff
- [ ] No secrets in code (use settings)

### Debugging Tips

1. **Enable debug logging**:
   ```bash
   # In .env
   LOGGING_LEVEL=DEBUG
   ```

2. **Use interactive docs**:
   - Test endpoints at http://localhost:8080/docs
   - See request/response schemas
   - Debug validation errors

3. **Check database state**:
   ```bash
   docker-compose exec db psql -U postgres portfolio
   ```

4. **View migrations**:
   ```bash
   alembic current  # Current version
   alembic history  # All migrations
   ```

5. **Check logs**:
   ```bash
   docker-compose logs -f app-backend
   ```

### Performance Considerations

1. **Database queries**:
   - Use eager loading for relationships
   - Avoid N+1 queries
   - Index frequently queried fields

2. **Connection pooling**:
   - Pool size: 10 base + 20 overflow
   - Recycle connections after 3600s

3. **Caching**:
   - Redis available but underutilized
   - Consider caching token prices, chain data

4. **Async operations**:
   - Don't block event loop
   - Use async libraries (asyncpg, httpx)

### Security Considerations

When adding features:

1. **Validate all inputs**: Use Pydantic schemas
2. **Use parameterized queries**: Never build SQL strings
3. **Encrypt sensitive data**: Use `EncryptedString` for secrets
4. **Hash passwords**: Always use `hash_password()`
5. **Use UUIDs in API**: Don't expose sequential IDs
6. **Check authorization**: Verify user can access resource
7. **Rate limiting**: Consider adding for production

### Documentation

When adding features, update:

1. **Inline comments**: For complex logic
2. **Docstrings**: For public functions
3. **API descriptions**: In route decorators
4. **README.md**: For user-facing changes
5. **CLAUDE.md**: For architectural changes (this file)

### Getting Help

**Resources**:
- **FastAPI docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy docs**: https://docs.sqlalchemy.org/
- **Pydantic docs**: https://docs.pydantic.dev/
- **Alembic docs**: https://alembic.sqlalchemy.org/

**Common Questions**:
- "How do I add a new table?" → See [Common Tasks](#common-tasks)
- "Why async everywhere?" → FastAPI is async-first for performance
- "How are balances calculated?" → See `backend/services/balance_calculator.py`
- "What's the dual ID strategy?" → See [Architecture](#architecture)

---

## Appendix: Environment Variables

### Application Settings
```bash
APP_NAME="BagTracker API"
LOGGING_LEVEL="INFO"         # DEBUG, INFO, WARNING, ERROR
BIND_HOST="0.0.0.0"
BIND_HOST_PORT=8080
```

### Uvicorn Configuration
```bash
UVICORN_WORKERS=4            # Number of worker processes
UVICORN_RELOAD=false         # Auto-reload on code changes (dev only)
TIMEOUT_KEEP_ALIVE=180       # Seconds
LIMIT_CONCURRENCY=1000       # Max concurrent connections
LIMIT_MAX_REQUESTS=10000     # Max requests before worker restart
```

### Database (PostgreSQL)
```bash
POSTGRES_HOST="portfolio-db"
POSTGRES_PORT=5432
POSTGRES_DB="portfolio"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="Pa55w0rD"  # CHANGE IN PRODUCTION!
DB_DRIVER_ASYNC="postgresql+asyncpg"
DB_DRIVER_SYNC="postgresql+psycopg"
```

### Redis
```bash
REDIS_HOST="redis"
REDIS_PORT=6379
REDIS_DB=0
```

### Security
```bash
SECRET_KEY="my-super-duper-secret-key"           # For JWT signing
ENCRYPTION_KEY="my-super-duper-encryption-key"   # For data encryption
ENCRYPTION_KEY_OLD=""                            # For key rotation
ALGORITHM="HS256"                                # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_KEY_ROTATION_DAYS=90
```

### Web3
```bash
WEB3_PROVIDER="https://mainnet.infura.io/v3/<API_KEY>"
INFURA_API_KEY="<your-infura-key>"
ALCHEMY_API_KEY="<your-alchemy-key>"
```

### Balance System
```bash
BALANCE_DUST_THRESHOLD=0.000001           # Ignore balances below this
BALANCE_SNAPSHOT_ENABLED=true             # Enable balance history
BALANCE_HOURLY_SNAPSHOTS=true
BALANCE_DAILY_SNAPSHOTS=true
BALANCE_PRICE_UPDATE_INTERVAL=300         # Seconds
BALANCE_HISTORY_RETENTION_DAYS=90         # Keep snapshots for 90 days
```

### External APIs
```bash
COINGECKO_API_KEY=""                      # Optional, for pro tier
COINGECKO_API_URL="https://api.coingecko.com/api/v3"
```

---

## Changelog

### Version 0.0.12 (Current)
- **BREAKING**: Documented TimescaleDB hypertable requirements
- Added comprehensive TimescaleDB Hypertables section
- Clarified composite primary key requirements for hypertables:
  - BalanceHistory
  - NFTBalanceHistory
  - CexBalanceHistory
- Emphasized PostgreSQL-only requirement (SQLite NOT supported)
- Updated test examples to use PostgreSQL instead of SQLite
- Updated Database Technology section with TimescaleDB details
- Added warnings about composite PK ordering for hypertables

### Version 0.0.11
- Multi-chain wallet support
- Transaction deletion fix
- Balance and balance history calculation improvements
- Transaction cancellation route renamed

### Version History
See git commit history for detailed changes.

---

**Document Maintained By**: AI assistants working on this codebase
**Last Review**: 2025-11-15
**Next Review**: When significant architectural changes are made
