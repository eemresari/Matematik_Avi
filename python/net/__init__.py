"""Gönderici (sender) katmanı: WebSocket (tarayıcı).

Unity/OSC hattı kaldırıldı (2026-09-15, plan G1) — oyun tamamen web'e
göçtüğü için `create_sender` artık tek bir uygulama döndürür. Arayüz
(`send_hand` / `send_absent` / `close`) korunur ki `main.py`'de hiçbir
çağrı yeri değişmesin.
"""

from .ws_sender import WsSender


def create_sender(cfg) -> WsSender:
    return WsSender(cfg)


__all__ = ["WsSender", "create_sender"]
