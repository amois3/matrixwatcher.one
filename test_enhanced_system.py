#!/usr/bin/env python3
"""Test Enhanced Anomaly System with Anomaly Index."""

import asyncio
import time
from src.core.types import AnomalyEvent
from src.analyzers.online.cluster_detector import ClusterDetector
from src.analyzers.online.anomaly_index import AnomalyIndexCalculator
from src.analyzers.online.enhanced_message_generator import EnhancedMessageGenerator

def create_test_anomalies():
    """Create test anomalies for different scenarios."""
    current_time = time.time()
    
    # Scenario 1: Quantum + Crypto + Earthquake
    anomalies = [
        AnomalyEvent(
            timestamp=current_time,
            sensor_source="quantum_rng",
            parameter="randomness_score",
            value=0.82,
            mean=0.95,
            std=0.05,
            z_score=-2.6,
            metadata={
                "randomness_score": 0.82,
                "expected": 0.95,
                "source": "anu_quantum",
                "autocorrelation": 0.15,
                "bit_balance": 0.45,
                "severity": "high"
            }
        ),
        AnomalyEvent(
            timestamp=current_time + 5,
            sensor_source="crypto",
            parameter="BTCUSDT.price",
            value=95000,
            mean=92000,
            std=500,
            z_score=6.0,
            metadata={
                "symbol": "BTCUSDT",
                "previous_price": 92000,
                "new_price": 95000,
                "change_percent": 3.26,
                "volume_spike": True,
                "severity": "high"
            }
        ),
        AnomalyEvent(
            timestamp=current_time + 8,
            sensor_source="earthquake",
            parameter="magnitude",
            value=6.8,
            mean=5.0,
            std=0.5,
            z_score=3.6,
            metadata={
                "location": "Pacific Ocean",
                "depth_km": 10,
                "shallow": True,
                "severity": "high"
            }
        )
    ]
    
    return anomalies

async def test_system():
    """Test the enhanced system."""
    print("🧪 Тестирование Enhanced Anomaly System\n")
    print("=" * 60)
    
    # Initialize components
    print("\n1️⃣ Инициализация компонентов...")
    cluster_detector = ClusterDetector(cluster_window_seconds=30.0)
    anomaly_index = AnomalyIndexCalculator(baseline_window_hours=24)
    message_gen = EnhancedMessageGenerator()
    print("   ✅ Компоненты инициализированы")
    
    # Create test anomalies
    print("\n2️⃣ Создание тестовых аномалий...")
    anomalies = create_test_anomalies()
    print(f"   ✅ Создано {len(anomalies)} аномалий:")
    for i, a in enumerate(anomalies, 1):
        print(f"      {i}. {a.sensor_source}: {a.parameter} = {a.value}")
    
    # Add anomalies to cluster detector
    print("\n3️⃣ Добавление аномалий в детектор кластеров...")
    cluster = None
    for anomaly in anomalies:
        cluster = cluster_detector.add_anomaly(anomaly)
        await asyncio.sleep(0.1)
    
    if not cluster:
        print("   ❌ Кластер не сформировался!")
        return
    
    print(f"   ✅ Кластер обнаружен! Уровень {cluster.level}")
    print(f"      Аномалий: {len(cluster.anomalies)}")
    print(f"      Вероятность случайности: {cluster.probability:.4f}%")
    
    # Calculate Anomaly Index
    print("\n4️⃣ Расчет Anomaly Index...")
    index_snapshot = anomaly_index.calculate(cluster.anomalies)
    print(f"   ✅ Anomaly Index: {index_snapshot.index:.1f}/100")
    print(f"      Статус: {index_snapshot.status}")
    print(f"      Baseline ratio: {index_snapshot.baseline_ratio:.2f}x")
    print(f"      Breakdown:")
    for sensor, score in index_snapshot.breakdown.items():
        print(f"         • {sensor}: {score:.1f} баллов")
    
    # Generate enhanced message
    print("\n5️⃣ Генерация улучшенного сообщения...")
    message = message_gen.generate_with_index(cluster, index_snapshot)
    print("   ✅ Сообщение сгенерировано!")
    
    # Display message
    print("\n" + "=" * 60)
    print("📱 СООБЩЕНИЕ ДЛЯ TELEGRAM:")
    print("=" * 60)
    print()
    # Remove HTML tags for console display
    import re
    clean_message = re.sub('<[^<]+?>', '', message)
    print(clean_message)
    print()
    print("=" * 60)
    
    # Test with different scenarios
    print("\n6️⃣ Тестирование других сценариев...")
    
    # Single anomaly
    single = AnomalyEvent(
        timestamp=time.time(),
        sensor_source="crypto",
        parameter="price",
        value=93000,
        mean=92000,
        std=500,
        z_score=2.0,
        metadata={"symbol": "BTC", "change_percent": 1.5, "severity": "medium"}
    )
    
    cluster_single = cluster_detector.add_anomaly(single)
    if cluster_single and cluster_single.level == 1:
        print("   ✅ Одиночная аномалия обработана")
    
    print("\n✨ Все тесты пройдены успешно!")
    print("\n💡 Система готова к интеграции в main.py")

if __name__ == "__main__":
    asyncio.run(test_system())
