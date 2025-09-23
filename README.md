# Bag Tracker 
### _Track Your Bags. Embrace the Rekt._


## Purpose
Bag Tracker is a tool designed to help users track their cryptocurrency investments. It allows users to input their bag holdings and provides insights into their investment performance.

## Getting Started
1. Clone the repository:
    ```shell
    git clone https://github.com/gearbox/bagtracker.git
    ```

1. Navigate to the project directory:
    ```shell
    cd bagtracker
    ```

1. Run the application using the following command:
    ```shell
    docker-compose up --build
    ```
    This command will build the Docker images and start the application.

1. Stop the application:
    ```shell
    docker-compose down
    ```

## Development
To set up a development environment, follow these steps:

### Setup

1. Install the UV packet manager following the [Instruction](https://github.com/astral-sh/uv) (standalone version is recommended)

1. Clone the repository (pass if you already did):
    ```shell
    git clone https://github.com/gearbox/bagtracker.git
    ```

1. Install the project dependancies
    Run the below commands in the project root directory:
    ```shell
    uv venv
    uv sync
    ```

    For developers it is recommended to install the `dev` dependencies as well:
    ```shell
    uv sync --group dev
    ```

1. Activate the virtual environment:
    ```shell
    source .venv/bin/activate
    ```

1. Run the application:
    - Using Fastapi:
        ```shell
        fastapi run backend/asgi.py --proxy-headers --port 80
        ```
    - Using Gunicorn:
        ```shell
        gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:80 --timeout 180 --access-logfile - --error-logfile - backend.asgi:app
        ```

### Using `ruff` linter
- Automatic run using `pre-commit`
    Run  `pre-commit install` in the project root directory.

    This way commands `ruff check --fix` and  `ruff format` will run after each commit using configuration from the `pyproject.toml`

- Manual run
    Run the below commands in the project root directory:
    ```shell
    ruff check --fix
    ruff format
    ```

### Using Alembic for Migrations
- To create a new migration:
    ```shell
    alembic revision --autogenerate -m "Your migration message"
    ```

- To apply migrations:
    ```shell
    alembic upgrade head
    ```

- To downgrade migrations:
    ```shell
    alembic downgrade -1
    ```
    or
    ```
    alembic downgrade base
    ```

- To view the current migration status:
    ```shell
    alembic current
    ```

### Seeding the Database
To seed the database with initial data, use the following command:
```shell
python -m backend.seeds.seed <table_name> <action>
```
Replace `<table_name>` with the name of the table you want to seed (e.g., `users`, `chains`, `tokens`), now supports `chains`.
You can write your own seeders in the `backend/seeds/data` directory.

Replace `<action>` with the desired action (supporting `seed`, `clear`, `status`).

For example:
- to seed the `chains` table, run:
    ```shell
    python -m backend.seeds.seed chains seed
    ```
- to clear the `chains` table, run:
    ```shell
    python -m backend.seeds.seed chains clear
    ```
- to check the status of the `chains` table, run:
    ```shell
    python -m backend.seeds.seed chains status
    ```
