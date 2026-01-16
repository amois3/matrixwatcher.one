#!/usr/bin/env python3
"""Simple test to send Telegram message."""
import asyncio
import json
from src.monitoring.telegram_bot import TelegramBot

async def main():
    with open("config.json") as f:
        config = json.load(f)
    
    bot = TelegramBot(
        token=config["alerting"]["telegram"]["token"],
        chat_id=config["alerting"]["telegram"]["chat_id"]
    )
    
    message = """🔴 ТЕСТОВАЯ АНОМАЛИЯ - Уровень 3

⚠️ Обнаружен кластер из 3 систем

📊 Детали:
• Crypto: BTC скачок на 3.26% ($92k → $95k)
• Quantum RNG: Снижение случайности (0.95 → 0.82)
• Earthquake: Магнитуда 6.8 в Тихом океане

🔗 Возможная связь: Геофизическое событие + квантовые флуктуации + рыночная реакция

⏰ Время: сейчас
🎯 Это тестовое сообщение для проверки системы"""
    
    print("📱 Отправляю тестовое сообщение...")
    success = await bot.send_message(message)
    if success:
        print("✅ Отправлено!")
    else:
        print("❌ Ошибка")

asyncio.run(main())
