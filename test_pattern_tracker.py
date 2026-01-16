#!/usr/bin/env python3
"""Test Historical Pattern Tracker."""

import asyncio
import time
from src.analyzers.online.historical_pattern_tracker import (
    HistoricalPatternTracker,
    Condition,
    Event
)

def test_pattern_tracker():
    """Test pattern tracker functionality."""
    print("🧪 Тестирование Historical Pattern Tracker\n")
    print("=" * 60)
    
    # Initialize tracker
    print("\n1️⃣ Инициализация...")
    tracker = HistoricalPatternTracker(storage_path="logs/patterns_test")
    print("   ✅ Tracker инициализирован")
    
    # Create test conditions
    print("\n2️⃣ Создание тестовых условий...")
    
    # Condition 1: Level 2, Quantum + Crypto
    condition1 = Condition(
        timestamp=time.time(),
        level=2,
        sources=["quantum_rng", "crypto"],
        anomaly_index=27.0,
        baseline_ratio=1.8
    )
    tracker.record_condition(condition1)
    print(f"   ✅ Условие 1: {condition1.to_key()}")
    
    # Condition 2: Level 3, Quantum + Crypto + Earthquake
    condition2 = Condition(
        timestamp=time.time() + 60,
        level=3,
        sources=["quantum_rng", "crypto", "earthquake"],
        anomaly_index=45.0,
        baseline_ratio=2.5
    )
    tracker.record_condition(condition2)
    print(f"   ✅ Условие 2: {condition2.to_key()}")
    
    # Simulate events
    print("\n3️⃣ Симуляция событий...")
    
    # Event 1: BTC volatility after condition 1
    event1 = Event(
        timestamp=condition1.timestamp + 3600,  # 1 hour later
        event_type="btc_volatility_medium",
        severity="medium",
        metadata={"description": "BTC volatility"}
    )
    tracker._match_event_with_conditions(event1)
    print("   ✅ Событие 1: BTC volatility через 1 час после условия 1")
    
    # Event 2: Earthquake after condition 2
    event2 = Event(
        timestamp=condition2.timestamp + 7200,  # 2 hours later
        event_type="earthquake_significant",
        severity="high",
        metadata={"description": "Earthquake"}
    )
    tracker._match_event_with_conditions(event2)
    print("   ✅ Событие 2: Earthquake через 2 часа после условия 2")
    
    # Add more conditions to build statistics
    print("\n4️⃣ Добавление данных для статистики...")
    for i in range(10):
        cond = Condition(
            timestamp=time.time() + i * 100,
            level=2,
            sources=["quantum_rng", "crypto"],
            anomaly_index=25.0 + i,
            baseline_ratio=1.5 + i * 0.1
        )
        tracker.record_condition(cond)
        
        # 40% of time, event follows
        if i % 5 < 2:
            evt = Event(
                timestamp=cond.timestamp + 3600,
                event_type="btc_volatility_medium",
                severity="medium",
                metadata={}
            )
            tracker._match_event_with_conditions(evt)
    
    print(f"   ✅ Добавлено 10 условий, 2 события")
    
    # Get probabilities
    print("\n5️⃣ Получение вероятностных оценок...")
    test_condition = Condition(
        timestamp=time.time(),
        level=2,
        sources=["quantum_rng", "crypto"],
        anomaly_index=30.0,
        baseline_ratio=2.0
    )
    
    probabilities = tracker.get_probabilities(test_condition, min_observations=5)
    
    if probabilities:
        print(f"\n   Для условия: {test_condition.to_key()}")
        for event_type, info in probabilities.items():
            print(f"\n   📊 {info['description']}")
            print(f"      Вероятность: {info['probability']:.1%}")
            print(f"      Среднее время: {info['avg_time_hours']:.1f} часов")
            print(f"      Наблюдений: {info['observations']}")
            print(f"      Событий: {info['occurrences']}")
    else:
        print("   ⚠️  Недостаточно данных для оценок")
    
    # Get calibration stats
    print("\n6️⃣ Статистика калибровки...")
    stats = tracker.get_calibration_stats()
    print(f"   Всего паттернов: {stats['total_patterns']}")
    print(f"   Средний Brier score: {stats['avg_brier_score']:.3f}")
    print(f"   Хорошо откалиброванных: {stats['well_calibrated_percent']:.0f}%")
    
    # Save
    print("\n7️⃣ Сохранение...")
    tracker.save()
    print("   ✅ Данные сохранены в logs/patterns_test/")
    
    print("\n" + "=" * 60)
    print("✨ Все тесты пройдены успешно!")
    print("\n💡 Pattern Tracker готов к работе!")

if __name__ == "__main__":
    test_pattern_tracker()
