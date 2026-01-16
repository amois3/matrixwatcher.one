#!/usr/bin/env python3
"""Test script to create synthetic anomaly cluster."""

import asyncio
import sys
import time
from src.core.event_bus import EventBus
from src.core.types import Event, EventType, AnomalyEvent
from src.monitoring.telegram_bot import TelegramBot
from src.analyzers.online.cluster_detector import ClusterDetector
from src.analyzers.online.message_generator import MessageGenerator
from src.config.config_manager import ConfigManager

async def main():
    """Create test anomaly cluster."""
    print("🧪 Создаю тестовую аномалию...")
    
    # Load config
    import json
    with open("config.json") as f:
        config_data = json.load(f)
    
    # Initialize components
    event_bus = EventBus()
    telegram = TelegramBot(
        token=config_data["alerting"]["telegram"]["token"],
        chat_id=config_data["alerting"]["telegram"]["chat_id"]
    )
    cluster_detector = ClusterDetector(
        cluster_window_seconds=10.0
    )
    message_generator = MessageGenerator()
    
    # Create 3 anomalies in quick succession
    anomalies = [
        AnomalyEvent(
            timestamp=time.time(),
            sensor_source="crypto",
            parameter="BTCUSDT.price",
            value=95000.0,
            expected_value=92000.0,
            deviation=3.26,
            severity="high",
            description="Резкий скачок цены BTC на 3.26%",
            metadata={
                "change_percent": 3.26,
                "previous_price": 92000.0,
                "new_price": 95000.0,
                "volume_spike": True
            }
        ),
        AnomalyEvent(
            timestamp=time.time() + 2,
            sensor_source="quantum_rng",
            parameter="randomness_score",
            value=0.82,
            expected_value=0.95,
            deviation=-0.13,
            severity="medium",
            description="Снижение случайности квантового генератора",
            metadata={
                "source": "anu_quantum",
                "autocorrelation": 0.15,
                "bit_balance": 0.45
            }
        ),
        AnomalyEvent(
            timestamp=time.time() + 5,
            sensor_source="earthquake",
            parameter="magnitude",
            value=6.8,
            expected_value=5.0,
            deviation=1.8,
            severity="high",
            description="Землетрясение магнитудой 6.8",
            metadata={
                "location": "Pacific Ocean",
                "depth_km": 10,
                "shallow": True
            }
        )
    ]
    
    print(f"📊 Создано {len(anomalies)} аномалий:")
    for i, anomaly in enumerate(anomalies, 1):
        print(f"  {i}. {anomaly.sensor_source}: {anomaly.description}")
    
    # Add to cluster detector
    cluster = None
    for anomaly in anomalies:
        cluster = cluster_detector.add_anomaly(anomaly)
        await asyncio.sleep(0.5)
    
    if cluster:
        print(f"\n🎯 Обнаружен кластер уровня {cluster.level}!")
        print(f"   Сенсоров: {len(set(a.sensor_source for a in cluster.anomalies))}")
        print(f"   Аномалий: {len(cluster.anomalies)}")
        
        # Generate message
        message = message_generator.generate_message(cluster)
        print(f"\n📱 Отправляю в Telegram...")
        print(f"\n{'-'*60}")
        print(message)
        print(f"{'-'*60}\n")
        
        # Send to Telegram
        success = await telegram.send_message(message)
        if success:
            print("✅ Сообщение отправлено!")
        else:
            print("❌ Ошибка отправки")
    else:
        print("\n⚠️ Кластер не сформировался")
    
    print("\n✨ Тест завершен!")

if __name__ == "__main__":
    asyncio.run(main())
