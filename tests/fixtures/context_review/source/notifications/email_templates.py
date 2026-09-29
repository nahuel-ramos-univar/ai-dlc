"""Email copy for order-related notifications."""

from __future__ import annotations

from orders.order_service import OrderPlacedEvent


def render_order_confirmation_email(event: OrderPlacedEvent) -> str:
    return (
        f"Thanks for your order {event.order_id}! "
        f"Total charged: ${event.total_cents / 100:.2f}."
    )
