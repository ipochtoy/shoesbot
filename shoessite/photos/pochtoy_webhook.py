"""Webhook для приема сигналов от Pochtoy API."""
import os
import json
import requests
from typing import Dict, Any


def send_telegram_message(chat_id: int, text: str) -> bool:
    """Отправить сообщение в Telegram."""
    try:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print("BOT_TOKEN not set")
            return False
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }, timeout=10)
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def handle_pochtoy_webhook(data: Dict[str, Any], admin_chat_id: int) -> Dict:
    """
    Обработать webhook от Pochtoy.
    
    Args:
        data: Данные от Pochtoy
        admin_chat_id: ID чата для уведомлений
    
    Returns:
        Response dict
    """
    try:
        # Парсим данные от Pochtoy
        event_type = data.get('event', 'unknown')
        message = data.get('message', '')
        trackings = data.get('trackings', [])
        status = data.get('status', '')
        
        print(f"Pochtoy webhook: {event_type}, status: {status}")
        
        # Формируем сообщение для Telegram
        telegram_text = f"📡 <b>Сигнал от Pochtoy</b>\n\n"
        
        if event_type:
            telegram_text += f"Событие: <code>{event_type}</code>\n"
        
        if status:
            telegram_text += f"Статус: <code>{status}</code>\n"
        
        if message:
            telegram_text += f"\n{message}\n"
        
        if trackings:
            telegram_text += f"\nТрекинги:\n"
            for t in trackings[:10]:  # Максимум 10
                telegram_text += f"  • <code>{t}</code>\n"
        
        # Отправляем в Telegram
        send_telegram_message(admin_chat_id, telegram_text)
        
        return {
            'success': True,
            'message': 'Webhook processed'
        }
        
    except Exception as e:
        print(f"Webhook processing error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

