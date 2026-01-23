# Удаление M5.0+ из Predictions - Завершено ✅

**Дата:** 18 января 2026  
**Статус:** Реализовано и работает

## Проблема

M5.0+ землетрясения происходят ~2 раза в день. Предсказание "в течение 7 часов" имеет базовую вероятность 61% просто потому, что окно покрывает почти половину дня.

Это не настоящее предсказание - это "пальцем в небо, все равно попадем".

## Решение

Убрали `earthquake_moderate` (M5.0+) из публичных predictions. Оставили только:
- **M6.0+** (earthquake_strong) - ~1 раз в 2.2 дня (по нашей статистике) = редко = интересно
- **M7.0+** (earthquake_major) - 0 за 38 дней наблюдений = очень редко = критично

### Наша реальная статистика (38 дней наблюдений)

```
M5.0+: 210 событий (~5.5 раз в день, каждые 4 часа)
M6.0+: 17 событий (~1 раз в 2.2 дня)
M7.0+: 0 событий (не было за период)
```

**Топ-3 самых сильных:**
1. M6.7 - 27 декабря 2025 - Тайвань
2. M6.7 - 7 января 2026 - Филиппины  
3. M6.7 - 10 января 2026 - Индонезия

## Реализация

### 1. Фильтр в `get_probabilities()` 
**Файл:** `src/analyzers/online/historical_pattern_tracker.py`  
**Строки:** 458-460

```python
# Skip earthquake_moderate (M5.0+) - too frequent, not meaningful
if event_type == "earthquake_moderate":
    logger.debug(f"Skipping earthquake_moderate for {condition_key}")
    continue
```

### 2. Фильтр в `_save_predictions_to_file()`
**Файл:** `main.py`  
**Строки:** 289-293

```python
active_predictions = [
    p for p in merged_predictions 
    if p.get("timestamp", 0) > cutoff
    and p.get("event") != "earthquake_moderate"  # Remove M5.0+
]
```

### 3. Фильтр в `_refresh_predictions_file()`
**Файл:** `main.py`  
**Строки:** 189-193

```python
active_predictions = [
    p for p in predictions 
    if p.get("timestamp", 0) > cutoff
    and p.get("event") != "earthquake_moderate"  # Remove M5.0+
]
```

### 4. Дополнительный фильтр по ширине окна
**Файл:** `src/analyzers/online/historical_pattern_tracker.py`  
**Строки:** 472-477

```python
# Filter by time window width for earthquakes
# Only show if window < 12 hours (precise prediction)
if 'earthquake' in event_type:
    if min_time_h is not None and max_time_h is not None:
        window_width = max_time_h - min_time_h
        if window_width >= 12.0:
            # Window too wide - not precise enough
            continue
```

## Результат

✅ **Файл predictions теперь пустой** - все M5.0+ удалены  
✅ **Система будет показывать только значимые события:**
- M6.0+ и M7.0+ землетрясения (редкие, важные)
- Крипто pump/dump (актуально для трейдеров)
- Солнечные бури (интересно для наблюдателей)

✅ **M5.0+ продолжают отслеживаться внутри** для:
- Накопления статистики
- Калибровки системы
- Анализа паттернов

Но НЕ показываются пользователям - только честные, значимые предсказания.

## Философия

> "Наблюдаем, не объясняем. Показываем только то, что действительно интересно."

Мы не скатываемся в "красивые цифры". Мы показываем только то, что имеет смысл.

## Проверка

```bash
# Проверить текущие predictions
python3 << 'EOF'
import json
d = json.load(open('logs/predictions/current.json'))
print(f'Всего: {len(d["predictions"])}')
events = set(p['event'] for p in d['predictions'])
print(f'События: {", ".join(sorted(events)) if events else "(пусто)"}')
EOF
```

Ожидаемый результат: `(пусто)` или только M6.0+/M7.0+/crypto события.

## Логи

Система логирует каждый refresh:
```
2026-01-18 21:57:57 [INFO] Refreshed predictions: 17 → 0 (removed 17 old/M5.0+)
```

Это значит фильтр работает правильно.
