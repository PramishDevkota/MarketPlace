"""Payment notification services.

Sends order/payment alerts to buyers and sellers through the channels that are
configured on the deployment (email always, WhatsApp when credentials are
present). Each sender fails gracefully so the marketplace never breaks because
of a notification problem.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_email(to, subject, body):
    """Send a plain-text email to a single recipient."""
    if not settings.EMAIL_HOST:
        logger.info('Email not sent to %s because SMTP is not configured.', to)
        return False
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=False,
        )
        logger.info('Email sent to %s: %s', to, subject)
        return True
    except Exception as exc:  # noqa: BLE001 - never crash the payment flow
        logger.warning('Emailing %s failed (%s).', to, exc)
        return False


def send_whatsapp(to_number, body):
    """Send a WhatsApp message via the Meta Cloud API (stub).

    Requires WHATSAPP_TOKEN + WHATSAPP_PHONE_ID in the environment. The message
    must match an approved Cloud API template; this is intentionally a stub so
    the provider call can be dropped in without touching the payment flow.
    """
    if not (settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID):
        logger.info('WhatsApp not sent to %s because credentials are missing.', to_number)
        return False
    # TODO: POST to https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages
    # with a templated text message payload. Left as a stub until a template is
    # approved. Logging only for now.
    logger.info('[stub] WhatsApp to %s: %s', to_number, body)
    return False


def _seller_phone(order):
    """Best known contact number for the order's seller."""
    user = order.seller
    request = user.seller_requests.exclude(phone_number='').order_by('-created_at').first()
    return (request.phone_number if request and request.phone_number else user.phone_number) or ''


def notify_seller_of_payment(order):
    """Alert the seller that an advance deposit has been paid for their product."""
    if not order or not order.seller:
        return False

    from django.urls import reverse

    product = order.product
    buyer_name = order.buyer.get_full_name() or order.buyer.username

    subject = f'You received a payment for "{product.name}"'
    order_url = order.get_absolute_url()

    body = (
        f'Hi {order.seller.get_full_name() or order.seller.username},\n\n'
        f'Good news! {buyer_name} has paid the advance deposit for your product:\n\n'
        f'   Product : {product.name}\n'
        f'   Quantity: {order.quantity}\n'
        f'   Total   : Rs. {order.total_price:,.2f}\n'
        f'   Deposit : Rs. {order.amount_paid:,.2f} (via Khalti)\n'
        f'   Balance : Rs. {order.remaining_amount:,.2f} due at delivery\n\n'
        f'Meet the buyer at: {order.get_meetup_location_display()}\n\n'
        f'You can view the full order here: '
        f'{settings.MARKETPLACE_BASE_URL}{order_url}\n\n'
        f'Thanks,\nIslington Marketplace'
    )

    whatsapp_body = (
        f'Payment received for "{product.name}" (x{order.quantity}). '
        f'Deposit Rs. {order.amount_paid:,.2f} paid via Khalti. '
        f'Meet buyer at {order.get_meetup_location_display()}. '
        f'Details: {settings.MARKETPLACE_BASE_URL}{order_url}'
    )

    sent = False
    if order.seller.email:
        sent = send_email(order.seller.email, subject, body) or sent

    phone = _seller_phone(order)
    if phone:
        sent = send_whatsapp(phone, whatsapp_body) or sent

    if not sent:
        logger.info('No notification channel available for order %s.', order.pk)
    return sent