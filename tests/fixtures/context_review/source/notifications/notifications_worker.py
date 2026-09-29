"""Long-polls the orders queue and sends an order-confirmation email.

This module does not send SMS. It only publishes an email confirmation and
announces that confirmation on NOTIFICATION_SENT_TOPIC so other modules can
react to it.
"""

from __future__ import annotations

from notifications.email_templates import render_order_confirmation_email
from orders.order_service import ORDER_PLACED_TOPIC, OrderPlacedEvent

NOTIFICATION_SENT_TOPIC = "notifications.order_confirmation_sent"


class NotificationsWorker:
    """Consumes OrderPlacedEvent and publishes a confirmation email."""

    def __init__(self, queue_client, email_client):
        self._queue_client = queue_client
        self._email_client = email_client

    def run_once(self) -> None:
        for event in self._queue_client.poll(ORDER_PLACED_TOPIC):
            self._handle(event)

    def _handle(self, event: OrderPlacedEvent) -> None:
        message = render_order_confirmation_email(event)
        self._email_client.send(event.customer_email, message)
        self._queue_client.publish(NOTIFICATION_SENT_TOPIC, event.order_id)
