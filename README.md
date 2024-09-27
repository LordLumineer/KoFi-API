<div align="center">

![KoFi-API logo](./img/bitmap.svg "KoFi-API logo")

# KoFi-API

An API to store and access Ko-fi donations

<!-- Badges -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Lint and Test](https://github.com/LordLumineer/KoFi-API/actions/workflows/lint_and_test.yml/badge.svg?branch=Master)](https://github.com/LordLumineer/KoFi-API/actions/workflows/lint_and_test.yml)

[![Pytest](./img/pytest_badge.svg)](./reports/pytest.md)
[![Pylint Score](./img/pylint_badge.svg)](./reports/pylint.txt)
[![Coverage](./img/coverage_badge.svg)](./reports/coverage.txt)
</div>

## About Ko-fi API

Ko-fi Donation API is a FastAPI-based system that allows users to manage Ko-fi donations, users, and transactions. It provides a set of API endpoints for handling donations, exporting and importing the database, and admin-specific operations like managing users and transactions.

## Table of Contents

- [KoFi-API](#kofi-api)
  - [About Ko-fi API](#about-ko-fi-api)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
    - [For testing purposes](#for-testing-purposes)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
  - [API Endpoints](#api-endpoints)
    - [Ko-fi Webhook Endpoints](#ko-fi-webhook-endpoints)
    - [User Management Endpoints](#user-management-endpoints)
    - [Admin Operations Endpoints](#admin-operations-endpoints)
    - [Database Management Endpoints](#database-management-endpoints)
  - [Running Tests](#running-tests)
  - [License](#license)
  - [Useful CMD](#useful-cmd)

## Features

- **User management:** Create, retrieve, update, and delete LOCAL Ko-fi users.
- **Donation transactions:** Record and query transactions from Ko-fi's webhook API.
- **Admin operations:** Access ALL Ko-fi transactions and users.
- **Database management:** Export and import the SQLite database, as well as recover the database from backups (ONLY available for admin users).

## Requirements

- [Python 3.10+](https://www.python.org/downloads/): Any Python 3.10+ version should be supported, built and tested using [`Python 3.12.6`](https://www.python.org/downloads/release/python-3126/).
- [FastAPI](https://fastapi.tiangolo.com/): A modern web framework for building APIs. The application uses [`FastAPI 0.115.0`](https://github.com/fastapi/fastapi/releases/tag/0.115.0) by default.
- [SQLAlchemy](https://www.sqlalchemy.org): A Python SQL toolkit and Object Relational Mapper (ORM) for database access.
- [APScheduler](https://apscheduler.readthedocs.io): A background job scheduler for Python, to remove every day data older than 30 days (default) from the database.
- [Alembic](https://alembic.sqlalchemy.org): A migration tool for SQLAlchemy.
- [Pydantic](https://docs.pydantic.dev): A data validation library for Python.

### For testing purposes

- [coverage](https://coverage.readthedocs.io/en/coverage-5.5/): A tool for measuring code coverage of Python programs.
- [pytest](https://docs.pytest.org/en/6.2.x/): A unit testing framework for Python.
- [pylint](https://pylint.pycqa.org/): A tool for static code analysis.

## Installation

To install and set up the project locally, follow these steps:

1. Clone the repository:

    ```bash
    git clone <https://github.com/yourusername/kofi-donation-api.git>
    cd kofi-donation-api
    ```

2. Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install dependencies:

    ```bash
    cd app
    pip install -r requirements.txt
    ```

4. Set up the environment variables:

- **`DATA_RETENTION_DAYS`:** Default data retention period for users. Default is `"30"`.
- **`ADMIN_SECRET_KEY`:** Secret key for admin operations. Default is `changethis`. An alert will be raised if the secret key is set to the default value.
- **`ENVIRONMENT`:** Provide the stage of the application. Possible values are `local` and `production`. Default is `local` and will not block if the secret key is set to the default value (in production it will block).

    ```bash
    DATA_RETENTION_DAYS="10"
    ADMIN_SECRET_KEY="your_admin_secret_key"
    ENVIRONMENT="production"
    ```

## Configuration

The application uses Pydantic to manage environment variables. The configuration variables can be defined in the .env file or passed as environment variables. Key configuration options include:

`PROJECT_NAME`: The name of the project. Default is `Ko-fi API`.
`DATA_RETENTION_DAYS`: Default data retention period for users. Default is `"30"`.
`DATABASE_URL`: The database connection URL (e.g., SQLite, PostgreSQL). Default is `sqlite:///./KoFi.db`.
`ADMIN_SECRET_KEY`: Secret key for admin operations. Default is `changethis`.
`ENVIRONMENT`: The environment in which the app is running (local, production). Default is `local`.

## Running the Application

You can run the FastAPI application using Uvicorn:

```bash
cd app
fastapi run main.py
```

The API will be accessible at <http://127.0.0.1:8000>, and the documentation will be available at <http://127.0.0.1:8000/docs> or <http://127.0.0.1:8000/redoc> (Swagger UI/ReDoc).

## API Endpoints

### Ko-fi Webhook Endpoints

- **POST** `/webhook`: Receives a Ko-fi transaction via a webhook and stores the transaction.

    You can find the different Ko-fi webhook events and more information about them [here](https://help.ko-fi.com/hc/en-us/articles/360004162298-Does-Ko-fi-have-an-API-or-webhook).

### User Management Endpoints

- **POST** `/users/{verification_token}`: Create a new user.
- **GET** `/users/{verification_token}`: Retrieve a user by their verification token.
- **PATCH** `/users/{verification_token}`: Update user data, such as data_retention_days.
- **DELETE** `/users/{verification_token}`: Delete a user and their associated transactions.

### Admin Operations Endpoints

- **GET** `/db/transactions`: Retrieve all Ko-fi transactions (admin-only).
- **GET** `/db/users`: Retrieve all Ko-fi users (admin-only).

### Database Management Endpoints

- **GET** `/db/export`: Export the database (admin-only).
- **POST** `/db/recover`: Recover the database from a file (admin-only).
- **POST** `/db/import`: Import a database (admin-only).

## Running Tests

The project uses pytest for testing. To run the tests, first install the development dependencies:

```bash
cd app
pip install -r test/requirements-dev.txt
```

Then, run the tests:

```bash
coverage run -m pytest
```

This will execute all unit tests, including those for the FastAPI endpoints and database operations.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

That's it! You're all set up to use the Ko-fi API.

## Useful CMD

```bash
pip install -r app/requirements.txt
pip install -r app/test/requirements-dev.txt

fastapi dev app/main.py
fastapi dev app/main.py --host 0.0.0.0

pylint app/ 
pylint app/ --fail-under=8 --output-format=parseable | tee reports/pylint-report.txt

pytest --tb=no --md-report --md-report-verbose=1
pytest --tb=no --md-report --md-report-output=reports/pytest.md

coverage run -m pytest --tb=no --md-report
coverage run -m pytest --tb=no --md-report --md-report-output=reports/pytest.md 
coverage report | tee reports/coverage.txt

cd app
alembic revision --autogenerate -m "describe your changes"
```
