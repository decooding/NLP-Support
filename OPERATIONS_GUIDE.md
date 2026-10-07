# Регламент подключения и передачи на сопровождение: Smart Support Dispatcher

Данный документ содержит исчерпывающее пошаговое руководство для инженеров сопровождения, дежурной смены (L2/L3), DevOps-инженеров и системных администраторов по развертыванию, интеграции, мониторингу и поддержке сервиса в промышленном контуре.

---

## 1. Архитектурный контекст сервиса

**Smart Support Dispatcher** — сервис автоматической двухуровневой классификации и диспетчеризации входящих заявок техподдержки:
1. **System 1 (Fast-Path / Laya):** Локальный не-авторегрессионный классификатор с калиброванной вероятностью (`answer_confidence`) и механизмом воздержания (`abstention`). Задержка $p95 \le 50$ мс (GPU) / $\le 300$ мс (CPU).
2. **System 2 (Deep-Path / Gemini):** Облачный LLM-анализ сложных случаев через Google GenAI API с жесткой валидацией Pydantic v2 и CoT.
3. **Resilience & HITL:** Встроенный Circuit Breaker (5 сбоев / 30с) с автоматическим переводом в статус `PENDING_MANUAL_REVIEW` при любых сетевых/модельных сбоях (сервис не падает с HTTP 500).

---

## 2. Чек-лист подготовки перед развертыванием (Pre-requisites)

Перед вводом в эксплуатацию необходимо запросить и подготовить следующие ресурсы:

### 2.1. Доступы и сетевая связность (Сетевые доступы / Firewall)
- [ ] **Входящий трафик:** Открытие порта `8000` (или `443` через Ingress/Reverse Proxy) для систем-источников заявок (Service Desk, Telegram-боты, Webhook-шлюзы).
- [ ] **Исходящий трафик к LLM:** Разрешить доступ к хосту API Gemini:
  - Домен: `generativelanguage.googleapis.com` (порт `443/TCP`).
  - При наличии корпоративного Forward Proxy — настроить переменные `HTTPS_PROXY` / `HTTP_PROXY`.
- [ ] **Секреты:** Получить API-токен Google Gemini API (`GEMINI_API_KEY`) и поместить его в безопасное хранилище секретов (HashiCorp Vault / Kubernetes Secret).

### 2.2. Аппаратные требования (Sizing)
- **Минимальные (CPU only):** 2 vCPU, 4 ГБ RAM, 10 ГБ SSD.
- **Рекомендуемые для нагрузки > 50 RPS:** 4 vCPU, 8 ГБ RAM (или 1x NVIDIA T4/A10G GPU для sub-50ms инференса System 1).

---

## 3. Конфигурация окружения (.env)

Создайте файл `.env` на целевом сервере на основе шаблона [`.env.example`](file:///d:/NLP-Support/.env.example):

```ini
# Общие настройки приложения
APP_NAME="Smart Support Dispatcher"
ENVIRONMENT="production"
DEBUG=false

# System 1 (Laya Fast-Path)
LAYA_MODEL_NAME=multilingual
LAYA_REVISION=main
LAYA_MIN_CONFIDENCE=0.85
LAYA_MAX_CONCURRENCY=4
LAYA_DEVICE=cpu

# System 2 (Gemini Fallback)
GEMINI_API_KEY="AIzaSy..."          # Ваш реальный API-ключ
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MIN_CONFIDENCE=0.70
GEMINI_TIMEOUT_SECONDS=3.5
GEMINI_MAX_RETRIES=2
SYSTEM2_TOTAL_BUDGET_SECONDS=10.0

# Отказоустойчивость (Circuit Breaker)
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS=30.0

# Кэш дедупликации и очередь модерации (HITL)
HITL_QUEUE_ENABLED=true
DEDUPLICATION_CACHE_TTL_SECONDS=3600
```

---

## 4. Развертывание и запуск (Deployment)

### Вариант А: Запуск в Docker / Docker Compose (Рекомендуемый)

1. Сборка production-образа:
```bash
docker build -t support-dispatcher:latest .
```

2. Запуск контейнера:
```bash
docker run -d \
  --name support-dispatcher \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  support-dispatcher:latest
```

### Вариант Б: Запуск в systemd (Bare-metal / VM)

1. Создать виртуальное окружение и установить пакет:
```bash
python -m venv /opt/nlp-support/.venv
/opt/nlp-support/.venv/bin/pip install /opt/nlp-support/
```

2. Создать unit-файл `/etc/systemd/system/support-dispatcher.service`:
```ini
[Unit]
Description=Smart Support Dispatcher Service
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/nlp-support
EnvironmentFile=/opt/nlp-support/.env
ExecStart=/opt/nlp-support/.venv/bin/uvicorn support_dispatcher.api.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Активировать и запустить:
```bash
systemctl daemon-reload
systemctl enable --now support-dispatcher
```

---

## 5. Интеграция с источниками обращений (API Контракт)

### 5.1. Классификация заявки (`POST /classify`)

**Запрос:**
```http
POST /classify HTTP/1.1
Host: dispatcher.internal:8000
Content-Type: application/json

{
  "ticket_id": "SD-2026-9812",
  "text": "Ошибка при согласовании приказа на отпуск сотрудника Иванова И.И. в модуле кадров.",
  "metadata": {
    "source_system": "telegram_bot",
    "user_id": "usr_441"
  }
}
```

**Ответ (200 OK):**
```json
{
  "ticket_id": "SD-2026-9812",
  "category": "DKA",
  "confidence": 0.94,
  "source": "system1",
  "status": "ROUTED",
  "trace_id": "trc-8f192b4a12",
  "model_version": "laya-multilingual",
  "reasoning": null,
  "draft_reply": null
}
```

### 5.2. Таксономия очередей для маршрутизации
Маршрутизатор сопоставляет категории с очередями Service Desk:
- `SED` $\rightarrow$ Очередь техподдержки СЭД / Канцелярии.
- `DKA` $\rightarrow$ Очередь кадрового делопроизводства / HR.
- `TECHNICAL_BUG` $\rightarrow$ Очередь инженерной поддержки / L3 Bug Tracking.
- `FEATURE_REQUEST` $\rightarrow$ Очередь управления продуктом / Product Backlog.
- `GENERAL_INQUIRY` $\rightarrow$ Первая линия техподдержки / Консультации.
- `OTHER` или статус `PENDING_MANUAL_REVIEW` $\rightarrow$ Очередь ручной модерации и доразметки (HITL).

---

## 6. Мониторинг, Healthcheck и алертинг (Observability)

### 6.1. Эндпоинты проверки здоровья
- `GET /health` — **Liveness probe** (возвращает `{"status": "healthy"}`). Проверяет доступность процесса.
- `GET /ready` — **Readiness probe** (возвращает `{"status": "ready"}`). Возвращает 200 только после загрузки и прогрева моделей в памяти. При инициализации отдает 503.

### 6.2. Метрики Prometheus (`GET /metrics`)
Подключите сборщик Prometheus к эндпоинту `/metrics`. Ключевые метрики для дашборда Grafana:
- `support_dispatcher_tickets_total{status, source, category}` — суммарный поток тикетов в разрезе статусов и категорий.
- `support_dispatcher_fallback_total{reason}` — частота ухода в fallback System 2 или ручную очередь.
- `support_dispatcher_system1_latency_seconds_bucket` — латентность быстрого контура.
- `support_dispatcher_system2_latency_seconds_bucket` — латентность внешнего вызова LLM.

### 6.3. Рекомендуемые алерты дежурной смены
1. **High Fallback Rate (Warning):** Доля переходов в System 2 превышает 35% за 15 минут (сигнал о деградации качества System 1 или изменении характера входящего потока).
2. **Circuit Breaker Open (Critical):** Ошибки обращения к Gemini API превысили лимит (5 подряд), вызовы приостановлены на 30с.
3. **HITL Queue Spill (Warning):** Размер очереди заявок со статусом `PENDING_MANUAL_REVIEW` превысил 100 заявок.

---

## 7. Регламент решения инцидентов (Troubleshooting / Runbook)

| Симптом | Вероятная причина | Действия дежурного инженера |
|---|---|---|
| `/ready` возвращает 503 | Модель System 1 не инициализирована или заблокирована | Проверить логи сервиса (`journalctl -u support-dispatcher` или `docker logs`). Убедиться в достаточности RAM (не менее 4 ГБ). |
| Массовый статус `PENDING_MANUAL_REVIEW` | Сработал Circuit Breaker из-за сбоя Google Gemini API | 1. Проверить квоты и баланс Google Cloud / Gemini API.<br>2. Проверить сетевой доступ к `generativelanguage.googleapis.com`.<br>3. Сервис продолжает работать штатно, перенаправляя неопределенные тикеты операторам L2. |
| Повышенная латентность > 1 сек на запрос | Очередь конкурентных запросов System 1 переполнена | Увеличить `LAYA_MAX_CONCURRENCY` в `.env` (при наличии свободных ядер CPU) либо переключить `LAYA_DEVICE=cuda`. |
| Ошибки дедупликации | Повторные отправки тикетов с тем же `ticket_id` | Корректное поведение сервиса: возвращается закешированный статус без повторного расхода ресурсов. При необходимости скорректировать `DEDUPLICATION_CACHE_TTL_SECONDS`. |

---

## 8. Процедура регламентных работ и обновления

1. **Обновление версий:**
   ```bash
   git pull origin main
   pip install --upgrade .
   pytest -v --cov=src --cov-fail-under=85
   systemctl restart support-dispatcher
   ```
2. **Переобучение и обновление порогов:**
   Собранные в модуле `review/` исправленные операторами тикеты выгружаются для обновления словарей и порогов калибровки `LAYA_MIN_CONFIDENCE` в файле конфигурации.
