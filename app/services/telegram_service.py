"""
Telegram bot service for notifications
"""
import os
import asyncio
import httpx
from typing import Optional

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.default_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    async def send_message(self, text: str, chat_id: str = None) -> bool:
        """Send a message via Telegram bot"""
        
        if not self.bot_token:
            return False
        
        target_chat_id = chat_id or self.default_chat_id
        if not target_chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload)
                return response.status_code == 200
        except:
            return False