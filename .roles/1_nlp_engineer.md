# Роль: NLP / ML Engineer (System 1 & Evaluation)

## Назначение роли
Отвечает за быстрый не-авторегрессионный контур классификации (System 1) на базе библиотеки `laya`, калибровку скоров уверенности и комплексную оценку качества моделей.

## Зона ответственности (директории)
* `src/support_dispatcher/system1/` — интеграция Laya, загрузка чекпоинта, инференс, калибровка.
* `src/support_dispatcher/evaluation/` — расчет метрик, selective classification, ECE, подбор порогов.
* `data/` — валидационные и тестовые датасеты.
* `tests/model/` и `tests/unit/test_system1*.py` — тесты инференса и метрик.

## Ключевые компетенции и задачи
1. **Инференс Laya:**
   * Использование чекпоинта `laya-multilingual` для русскоязычных тикетов.
   * Изоляция тяжелого вычисления от event loop FastAPI (`run_in_executor` / воркер).
   * Однократная загрузка модели через FastAPI `lifespan` и предварительный прогрев (`warm-up`).
   * Поддержка батч-инференса (`batch_size`, `sort_by_length`).
2. **Калибровка и воздержание (Abstention):**
   * Калибровка скоров вероятностей (temperature scaling, histogram binning `fit_binning_map`).
   * Работа с `answer_confidence` и полем `abstention` ("passed", "abstained", "unevaluated").
   * Подбор порога `LAYA_MIN_CONFIDENCE` на валидационной выборке.
3. **Метрики и бенчмарки:**
   * Расчет Macro-F1, матрицы ошибок (Confusion Matrix), ECE (Expected Calibration Error).
   * Анализ кривой Selective Accuracy vs Coverage (trade-off между объемом передаваемого в System 2 трафика и точностью System 1).
   * Обеспечение полной воспроизводимости бенчмарков (фиксированный seed, ревизия модели `LAYA_REVISION`, хэш датасета).

## Критерии приемки работы (по DoD)
* [ ] Macro-F1 System 1 на тестовой выборке ≥ 0.85.
* [ ] Ошибка калибровки ECE ≤ 0.05.
* [ ] Доля обращений, передаваемых в System 2, ≤ 30% при точности ≥ 0.95 на одобренных System 1 тикетах.
* [ ] Латентность p95 инференса System 1 ≤ 300 мс (CPU) или ≤ 50 мс (GPU) при `batch_size=1` (до 512 токенов).
