# Инструкция по обновлению Matrix Watcher

## Что добавлено:

### 1. Anomaly Index Calculator (`src/analyzers/online/anomaly_index.py`)
- Рассчитывает общий скор 0-100
- Сравнивает с baseline (норма за 24 часа)
- Взвешивает разные сенсоры (Quantum RNG важнее)

### 2. Enhanced Message Generator (`src/analyzers/online/enhanced_message_generator.py`)
- Подробные объяснения для каждой аномалии
- Понятные интерпретации
- Контекст и связи между событиями

## Что нужно сделать:

### Шаг 1: Обновить main.py

Добавить импорты:
```python
from src.analyzers.online.anomaly_index import AnomalyIndexCalculator
from src.analyzers.online.enhanced_message_generator import EnhancedMessageGenerator
```

Добавить в `__init__`:
```python
self.anomaly_index = AnomalyIndexCalculator(baseline_window_hours=24)
self.enhanced_message_gen = EnhancedMessageGenerator()
```

Обновить `_handle_anomaly`:
```python
async def _handle_anomaly(self, anomaly):
    # Record for smart analysis
    self.smart_analyzer.record_anomaly(anomaly)
    
    # Detect cluster
    cluster = self.cluster_detector.add_anomaly(anomaly)
    
    if not cluster:
        return
    
    # Calculate Anomaly Index
    recent_anomalies = [a for a in cluster.anomalies]
    index_snapshot = self.anomaly_index.calculate(recent_anomalies)
    
    # Generate enhanced message
    message = self.enhanced_message_gen.generate_with_index(cluster, index_snapshot)
    
    # Send to Telegram
    if self.telegram:
        await self.telegram.send_message(message)
    
    # Save to logs
    self.storage.write_anomaly({
        "cluster": cluster.__dict__,
        "index": index_snapshot.__dict__,
        "timestamp": time.time()
    })
```

### Шаг 2: Добавить логирование Anomaly Index

Создать периодическую задачу (каждую минуту):
```python
async def log_anomaly_index():
    recent = self.smart_analyzer.get_recent_anomalies(window_seconds=300)
    snapshot = self.anomaly_index.calculate(recent)
    
    self.storage.write_record("anomaly_index", {
        "timestamp": snapshot.timestamp,
        "index": snapshot.index,
        "breakdown": snapshot.breakdown,
        "baseline_ratio": snapshot.baseline_ratio,
        "status": snapshot.status
    })

# Register task
self.scheduler.register_task("anomaly_index_logger", 
                             lambda: asyncio.run(log_anomaly_index()), 
                             interval=60.0)
```

## Результат:

Теперь сообщения будут выглядеть так:

```
🔴 Anomaly Index: 85/100

⚠️ Высокая активность (в 2.8 раза выше нормы)

━━━━━━━━━━━━━━━━━━━━━━

🎲 Quantum RNG: 35 баллов
Случайность: 82% (норма 95%)
Источник: квантовый вакуум (Австралия)
→ Квантовые числа показывают паттерны
→ Возможный "глитч" в случайности
→ Числа коррелируют (r=0.15)

💰 Crypto: 30 баллов
BTC: $92,000 → $95,000 (+3.26%)
→ Резкий рост за короткое время
→ Объем торгов резко вырос

🌍 Earthquake: 20 баллов
Магнитуда 6.8 в Pacific Ocean
Глубина: 10 км (мелкое, более опасное)
→ Сильное землетрясение
→ Возможны разрушения

━━━━━━━━━━━━━━━━━━━━━━

🔗 Возможная связь:
Квантовые флуктуации перед геофизическим событием
→ Возможное влияние на квантовый уровень

⏰ 13 декабря, 17:45
📊 Кластер уровня 3
🎲 Вероятность случайности: 0.001%
```

## Дополнительно:

Все подробные данные сохраняются в:
- `logs/crypto/` - каждая цена
- `logs/quantum_rng/` - каждое измерение
- `logs/anomaly_index/` - индекс каждую минуту
- `logs/anomalies/` - полные кластеры с деталями
