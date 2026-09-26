"""
core/notifier.py
================
Unified notification dispatcher for AIAutoShorts.
Handles alerting and event dispatch to external channels (Telegram, webhooks).
Fails silently and gracefully when credentials are not configured or external APIs are unreachable.
"""

import os
import requests
from typing import Optional, Dict, Any
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _is_valid_telegram_config() -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    tok = str(TELEGRAM_BOT_TOKEN).lower().strip()
    if not tok or "your_telegram_bot_token" in tok or "1234567890" in tok:
        return False
    return True


def send_notification(text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """
    Dispatches a text notification to configured channels.
    Currently supports Telegram Bot API with silent error handling.
    """
    if not _is_valid_telegram_config():
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        resp = requests.post(url, json=payload, timeout=5.0)
        return resp.status_code == 200
    except Exception as e:
        print(f"[Notifier] Notification dispatch skipped/failed: {e}", flush=True)
        return False


def send_message(text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """
    Backward-compatibility alias for send_notification.
    """
    return send_notification(text=text, reply_markup=reply_markup)


__all__ = [
    "send_notification",
    "send_message",
]
