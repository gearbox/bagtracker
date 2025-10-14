# Bag Tracker 💰
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
    - Using asgi.py
        ```shell
        python -m backend.asgi
        ```
    - Using direct Uvicorn
        ```shell
        python -m uvicorn backend.asgi:app --reload --host 0.0.0.0 --port 8080
        ```

### Setting up the application name and version
We use the `pyproject.toml` project fields `name` and `version` (semver versioning syle).
During the Docker container build process docker runs the `scripts/extract_version.py` script and generates `backend/_version.py` with the corresponding version. 
If you run the project locally and there is no generated `backend/_version.py` file, it will fall back to the `0.0.0-dev` version (will be shown in the Swagger UI). If you would like to see the actual app version, you can run the `scripts/extract_version.py` script manually by running the following command in your terminal from the root directory of the project:
```shell
python scripts/extract_version.py
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

### Uvicorn configuration
The Uvicorn configuration is located in the `uvicorn_config.py` file.
It is recommended to verify the config validity after any manual changes using the `scripts/verify_uvicorn_config.py` script by running the command from the project root directory:
```shell
python scripts/verify_uvicorn_config.py
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
### Updating files in the `static` folder (openapi/swagger, redoc)
The project uses locally hosted OpenAPI/Swagger UI assets for reliability. These files are stored in `static/openapi/` and include:

- `swagger-ui-bundle.js` - Swagger UI JavaScript bundle
- `swagger-ui.css` - Swagger UI styles
- `redoc.standalone.js` - ReDoc standalone bundle
- `favicon.png` - FastAPI favicon

#### The Python script is provided to download/update these assets from official CDN sources
```shell
# Update to latest versions
python scripts/update_openapi_assets.py

# Update to specific versions
python scripts/update_openapi_assets.py --swagger-version 5.10.0 --redoc-version 2.1.0

# Skip favicon download
python scripts/update_openapi_assets.py --skip-favicon

# View help
python scripts/update_openapi_assets.py --help
```
**Requirements:** `requests` library (already in project dependencies)

#### Manual Update

If you prefer to manually download the files:

1. **Swagger UI**: Visit https://github.com/swagger-api/swagger-ui/releases
   - Download `swagger-ui-bundle.js` and `swagger-ui.css` from the `dist` folder

2. **ReDoc**: Visit https://github.com/Redocly/redoc/releases
   - Download `redoc.standalone.js` from the bundles

3. Place all files in the `static/openapi/` directory

#### Verifying Assets

After updating, test the documentation endpoints:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

The assets should load without errors in the browser console.
