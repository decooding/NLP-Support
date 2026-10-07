# Роль: Backend & Domain Engineer (Architecture & Pipeline)

## Назначение роли
Отвечает за ядро приложения, доменную модель, сквозную оркестрацию пайплайна (System 1 -> PII -> System 2 -> Routing/HITL), маршрутизацию результатов и веб-интерфейс API.

## Зона ответственности (директории)
* `src/support_dispatcher/domain/` — модели Pydantic v2 (Ticket, ClassificationResult, таксономия, статусы).
* `src/support_dispatcher/core/` — конфигурация (`BaseSettings`), исключения, константы.
* `src/support_dispatcher/preprocessing/` — валидация, очистка текста, дедупликация тикетов.
* `src/support_dispatcher/pipeline/` — оркестратор классификации и принятия решений.
* `src/support_dispatcher/routing/` — отправка в Service Desk, очереди и вебхуки.
* `src/support_dispatcher/review/` — очереди Human-in-the-Loop (`PENDING_MANUAL_REVIEW`) и сбор датасета.
* `src/support_dispatcher/api/` — роутеры FastAPI, lifespan, dependency injection.
* `tests/unit/` (домен, пайплайн, препроцессинг) и `tests/integration/test_api*.py`.

## Ключевые компетенции и задачи
1. **Доменные сущности и типизация:**
   * Строгая типизация через Pydantic v2 (без динамических структур, 100% покрытие тайп-хинтами под `mypy --strict`).
   * Единый источник правды для таксономии категорий и контракта API (`ticket_id`, `category`, `confidence`, `source`, `status`, `trace_id`, `model_version`).
   * Применение правил разрешения конфликтов категорий (предметная область приоритетнее типа проблемы: например, ошибка в СЭД -> `SED`).
2. **Оркестрация пайплайна:**
   * Асинхронный конвейер обработки:
     `Incoming Ticket` -> `Validation/Deduplication` -> `System 1` -> [Уверен?] 
     -> Да: `Routing`
     -> Нет: `PII Masking` -> `System 2` -> [Уверен/Валиден?] 
        -> Да: `Routing`
        -> Нет: `HITL (PENDING_MANUAL_REVIEW)`
   * Гарантия того, что инференс моделей и I/O вызовы не блокируют event loop.
3. **Конфигурация:**
   * Загрузка всех параметров (`LAYA_MIN_CONFIDENCE`, `GEMINI_MODEL`, таймауты, ключи) через `pydantic-settings` из `.env`.

## Критерии приемки работы (по DoD)
* [ ] Код проходит `mypy --strict src/` без ошибок.
* [ ] Пайплайн полностью асинхронен (`async/await`) и устойчив к сбоям компонентов.
* [ ] Эндпоинты `/docs` отдают актуальную OpenAPI-схему со строгими типами.
* [ ] Реализована дедупликация повторных обращений с идентичным `ticket_id`.
