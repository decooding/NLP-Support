# Smart Support Dispatcher

Высокопроизводительный сервис автоматической двухуровневой классификации и маршрутизации входящих обращений технической поддержки.

## Архитектура
- **System 1 (Fast-Path):** Не-авторегрессионный классификатор Laya с калиброванной уверенностью (`answer_confidence`) и избирательным воздержанием (`abstention`).
- **System 2 (Deep-Path):** Анализ сложных контекстов через Google Gemini API со строгой Pydantic-схемой и Chain-of-Thought рассуждениями.
- **Resilience:** Circuit Breaker (5 ошибок / 30с таймаут) и плавный перевод в Human-in-the-Loop (`PENDING_MANUAL_REVIEW`).
- **Observability:** Prometheus-метрики (`/metrics`), распределенный трейсинг `trace_id` и аудит-логирование.

## Запуск проекта

1. Установка зависимостей:
```bash
pip install -e ".[dev]"
```

2. Запуск сервиса FastAPI:
```bash
uvicorn support_dispatcher.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

3. Запуск проверок качества и тестов:
```bash
ruff check src/
ruff format --check src/
mypy --strict src/
pytest -v --cov=src --cov-fail-under=85
```

## Эндпоинты
- `POST /classify` — классификация обращения
- `GET /health` — liveness probe
- `GET /ready` — readiness probe (готовность и прогрев моделей)
- `GET /metrics` — Prometheus метрики
- `GET /docs` — интерактивная документация Swagger/OpenAPI
