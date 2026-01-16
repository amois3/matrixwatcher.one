#!/usr/bin/env python3
"""Setup script for Telegram bot.

Run this script, then send any message to your bot in Telegram.
The script will detect your chat_id and update config.json.
"""

import asyncio
import json
import aiohttp

TOKEN = "8522165793:AAH5Tq4k_TS4jXELKJcva1lWkjm8mNRVrbc"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


async def get_updates():
    """Get updates from Telegram."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/getUpdates") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", [])
            else:
                print(f"Error: {response.status}")
                return []


async def send_test_message(chat_id: str):
    """Send test message."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "chat_id": chat_id,
            "text": "🚀 <b>Matrix Watcher подключен!</b>\n\nТеперь вы будете получать уведомления о:\n• 🔴 Аномалиях\n• 🔗 Корреляциях\n• ⚡ Причинно-следственных связях\n• 🚨 Кластерах\n• 🔮 Предвестниках",
            "parse_mode": "HTML"
        }
        async with session.post(f"{BASE_URL}/sendMessage", json=payload) as response:
            return response.status == 200


async def main():
    print("=" * 50)
    print("Matrix Watcher - Telegram Setup")
    print("=" * 50)
    print()
    print("Проверяю подключение к боту...")
    
    updates = await get_updates()
    
    if not updates:
        print()
        print("⚠️  Сообщений пока нет.")
        print()
        print("Пожалуйста:")
        print("1. Откройте Telegram")
        print("2. Найдите бота: @matrix_watcher_bot")
        print("3. Нажмите /start или отправьте любое сообщение")
        print("4. Запустите этот скрипт снова")
        print()
        return
    
    # Get the latest message
    latest = updates[-1]
    message = latest.get("message", {})
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    username = chat.get("username", "")
    first_name = chat.get("first_name", "")
    
    if not chat_id:
        print("❌ Не удалось получить chat_id")
        return
    
    print(f"✅ Найден чат!")
    print(f"   Chat ID: {chat_id}")
    print(f"   Username: @{username}" if username else f"   Name: {first_name}")
    print()
    
    # Update config.json
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        if "alerting" not in config:
            config["alerting"] = {}
        
        config["alerting"]["enabled"] = True
        config["alerting"]["telegram"] = {
            "enabled": True,
            "token": TOKEN,
            "chat_id": chat_id,
            "cooldown_seconds": 60
        }
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("✅ config.json обновлён!")
        print()
        
        # Send test message
        print("Отправляю тестовое сообщение...")
        if await send_test_message(chat_id):
            print("✅ Тестовое сообщение отправлено!")
            print()
            print("=" * 50)
            print("Готово! Теперь запустите: python3 main.py")
            print("=" * 50)
        else:
            print("❌ Не удалось отправить сообщение")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
