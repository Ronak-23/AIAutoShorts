"""
core/telegram_bot.py
====================
Backward compatibility shim forwarding to core.notifier.
The old 575-line polling daemon has been superseded by the FastAPI
web app and real-time SSE streaming console.
"""

from core.notifier import send_notification, send_message

__all__ = [
    "send_notification",
    "send_message",
]
