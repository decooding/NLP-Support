# Реестр ролей и протокол Loop-архитектуры

Разработка проекта **Smart Support Dispatcher** организована по принципу **«Агент проверяет Агента» (Producer-Reviewer Loop)** под управлением сценария оркестрации.

---

## 1. Карта ролей и парная валидация

| Роль | Файл роли | Зона ответственности | Роль в цикле (Loop) | Партнер по ревью (Критик) | Модель |
|---|---|---|---|---|---|
| **1. NLP / ML Engineer** | [1_nlp_engineer.md](file:///d:/NLP-Support/.roles/1_nlp_engineer.md) | `system1/`, `evaluation/`, `data/` | **Producer** (Laya, ECE, F1, Selective Accuracy) | QA / DevOps Agent | Claude Sonnet 5.5|
| **2. LLM & Safety Engineer** | [2_llm_safety_engineer.md](file:///d:/NLP-Support/.roles/2_llm_safety_engineer.md) | `system2/`, `privacy/` | **Producer** (Gemini API, PII masking, Prompts) | QA / DevOps Agent | Claude Sonnet 5.5  |
| **3. Backend & Domain Engineer**| [3_backend_engineer.md](file:///d:/NLP-Support/.roles/3_backend_engineer.md) | `domain/`, `core/`, `pipeline/`, `api/`, `routing/`, `review/` | **Producer** (Pydantic v2, FastAPI, Orchestration) | QA / DevOps Agent | Gemini 3.1 Pro|
| **4. QA & DevOps Engineer** | [4_qa_devops_engineer.md](file:///d:/NLP-Support/.roles/4_qa_devops_engineer.md) | `tests/`, `resilience/`, `observability/`, `Dockerfile` | **Gatekeeper & Reviewer** (Проверка DoD, `mypy`, `ruff`, `pytest`, Circuit Breaker) | Orchestrator | Gemini 3.8 Flash|
| **5. Researcher & Paper Author**| [5_researcher_paper_author.md](file:///d:/NLP-Support/.roles/5_researcher_paper_author.md) | `paper/` (`aticle.md`) | **Producer** (Научная статья, анализ затрат/задержек) | Team Lead / User | Gemini 3.8 Flash|

---

## 2. Протокол взаимодействия в цикле (Review Protocol)

Для каждого этапа разработки запускается итеративный цикл:

```text
[Оркестратор: Назначение фазы]
          │
          ▼
    [Исполнитель (Producer)] ◄─────────────────────────┐
    (Пишет код модуля + базовые тесты)                 │
          │                                            │
          ▼                                            │ Ошибки / Замечания
    [Ревьюер (QA Gatekeeper)]                          │ (до 3 итераций)
    (Запускает mypy, ruff, pytest, пишет edge-cases)   │
          │                                            │
    Вынесение вердикта:                                │
    ├── VERDICT: REJECTED ─────────────────────────────┘
    │   (с логами терминала и инструкциями по фиксу)
    │
    └── VERDICT: APPROVED
        (DoD выполнен, переход к следующей фазе)
```

### Контракт ответа QA-ревьюера
```text
VERDICT: APPROVED | REJECTED
FAILED_CHECKS: [список непройденных пунктов DoD или упавших проверок]
TRACEBACK_OR_ERRORS: [точные выдержки из терминала]
FIX_INSTRUCTIONS: [конкретные шаги по исправлению для исполнителя]
```
