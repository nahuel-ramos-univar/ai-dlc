"""Owns order creation and publishes an OrderPlacedEvent on success."""

from __future__ import annotations

from dataclasses import dataclass

ORDER_PLACED_TOPIC = "orders.order_placed"


@dataclass(frozen=True)
class OrderPlacedEvent:
    order_id: str
    customer_email: str
    total_cents: int


class OrderService:
    """Creates orders and publishes OrderPlacedEvent to the shared queue."""

    def __init__(self, queue_client):
        self._queue_client = queue_client

    def place_order(self, order_id: str, customer_email: str, total_cents: int) -> None:
        event = OrderPlacedEvent(order_id, customer_email, total_cents)
        self._queue_client.publish(ORDER_PLACED_TOPIC, event)
