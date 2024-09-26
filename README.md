# KoFi-API

[![Pylint Score](./img/pylint_badge.svg)](./app/pylint.json)
[![Coverage](./img/coverage_badge.svg)](./app/coverage.json)

## Useful CMD

```bash
alembic revision --autogenerate -m "describe your changes"
fastapi dev ./main.py --host 0.0.0.0
uvicorn main:app --host 0.0.0.0
fastapi dev ./main.py
coverage run -m pytest
coverage html
```
