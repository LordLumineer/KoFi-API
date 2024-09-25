# KoFi-API

![Pylint Score](https://github.com/LordLumineer/KoFi-API/actions/workflows/lint_and_test.yml/badge.svg)

## Useful CMD

```bash
alembic revision --autogenerate -m "describe your changes"
fastapi dev ./main.py --host 0.0.0.0
uvicorn main:app --host 0.0.0.0
fastapi dev ./main.py
coverage run -m pytest
coverage html
```
