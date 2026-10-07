---
title: Laya System 1 Classifier Server
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Laya System 1 Classifier (Hugging Face Spaces Docker Server)

Высокопроизводительный сервер не-авторегрессионной классификации обращений техподдержки **System 1 (Fast-Path)** для проекта **Smart Support Dispatcher**.

## Особенности
- **Суб-50мс задержка** на GPU / суб-300мс на CPU.
- **Калиброванная оценка уверенности** (`confidence`) и механизм воздержания (`abstention`).
- Предметные приоритеты таксономии DoD: `SED`, `DKA`, `TECHNICAL_BUG`, `FEATURE_REQUEST`, `GENERAL_INQUIRY`, `OTHER`.
- Полная совместимость с бесплатным Docker-инстансом Hugging Face Spaces (порт 7860).

## API Эндпоинты

### `GET /health`
Liveness/readiness проверка.
```bash
curl http://localhost:7860/health
```

### `POST /classify`
Классификация текста обращения.
```bash
curl -X POST http://localhost:7860/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Входящее письмо не регистрируется в канцелярии СЭД"}'
```

Ответ:
```json
{
  "category": "SED",
  "confidence": 0.98,
  "abstention": "passed",
  "raw_scores": {
    "SED": 6.0,
    "DKA": 0.0,
    "TECHNICAL_BUG": 0.0,
    "FEATURE_REQUEST": 0.0,
    "GENERAL_INQUIRY": 0.0,
    "OTHER": 0.2
  }
}
```
