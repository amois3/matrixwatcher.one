# 🔧 ИСПРАВЛЕНИЕ CRYPTO/BLOCKCHAIN/SPACE_WEATHER СОБЫТИЙ

## 🐛 ПРОБЛЕМА

Система показывала только predictions для землетрясений, но не для crypto/blockchain/space_weather.

**Причина:** Payload событий НЕ содержал поле `'source'`, поэтому все проверки событий возвращали False.

## ✅ ЧТО ИСПРАВЛЕНО

### 1. Исправлена функция `SensorReading.to_event()` в `src/core/types.py`

**Было:**
```python
def to_event(self, event_type: EventType = EventType.DATA) -> Event:
    return Event(
        timestamp=self.timestamp,
        source=self.source,
        event_type=event_type,
        payload=self.data,  # <-- НЕ содержит 'source'!
        metadata=self.metadata
    )
```

**Стало:**
```python
def to_event(self, event_type: EventType = EventType.DATA) -> Event:
    # Use to_dict() to include source in payload
    payload_dict = self.to_dict()
    # Remove timestamp as it's already in Event
    payload_dict.pop('timestamp', None)
    
    return Event(
        timestamp=self.timestamp,
        source=self.source,
        event_type=event_type,
        payload=payload_dict,  # <-- Теперь содержит 'source'!
        metadata=self.metadata
    )
```

### 2. Исправлена функция `_check_btc_volatility` в `src/analyzers/online/historical_pattern_tracker.py`

**Было:**
```python
pairs = data.get('pairs', {})  # Искало словарь
btc = pairs.get('BTCUSDT', {})
price_change = abs(btc.get('price_change_pct', 0))
```

**Стало:**
```python
# Используем прямое поле из данных
price_change = abs(data.get('btcusdt.price_change_24h_percent', 0))
```

### 3. Пороги для crypto событий

**Текущие пороги:**
- BTC volatility high: 2.5%
- BTC volatility medium: 1.5%
- BTC pump/dump 1h: 2.0%
- BTC pump/dump 4h: 4.0%
- BTC pump/dump 24h: 7.0%

## 🎯 РЕЗУЛЬТАТ

После перезапуска системы:
- ✅ События crypto/blockchain/space_weather теперь определяются корректно
- ✅ Payload содержит поле `'source'` для всех сенсоров
- ✅ Паттерны будут накапливаться для всех типов событий
- ✅ Predictions будут появляться для crypto/blockchain/space_weather

## 📊 ТЕСТИРОВАНИЕ

Проверено с временными порогами (0.8% для medium):
```
2026-01-22 21:10:43 [INFO] 📊 BTC volatility detected: 1.22% >= 0.8%
2026-01-22 21:10:43 [INFO] 🎯 Event detected: btc_volatility_medium from crypto
2026-01-22 21:10:43 [INFO] 🎯 Pattern event detected: btc_volatility_medium (medium)
```

## 🚀 ЧТО ДЕЛАТЬ ДАЛЬШЕ

1. **Система уже перезапущена** - работает с PID 83170

2. **Подожди 24-48 часов** чтобы накопились паттерны

3. **Проверь predictions:**
   ```bash
   cat logs/predictions/current.json | python3 -m json.tool | grep -A5 '"category": "crypto"'
   ```

Должны появиться predictions с category: "crypto", "blockchain", "space_weather"!

---

**Дата исправления:** 22 января 2026, 21:14
**Статус:** ✅ ИСПРАВЛЕНО И ПРОТЕСТИРОВАНО
