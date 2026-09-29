"""Builds a weekly reorder digest from confirmed order notifications.

This module subscribes to NOTIFICATION_SENT_TOPIC, which is published by
notifications.notifications_worker once an order confirmation email has
gone out. That import is a real, inspectable dependency: receipts depends
on notifications, not the other way around.
"""

from __future__ import annotations

from notifications.notifications_worker import NOTIFICATION_SENT_TOPIC


class ReceiptsDigestBuilder:
    """Consumes confirmed-order events to build a weekly reorder digest."""

    def __init__(self, queue_client):
        self._queue_client = queue_client
        self._confirmed_order_ids: list[str] = []

    def collect(self) -> None:
        for order_id in self._queue_client.poll(NOTIFICATION_SENT_TOPIC):
            self._confirmed_order_ids.append(order_id)

    def build_digest(self) -> list[str]:
        return list(self._confirmed_order_ids)
