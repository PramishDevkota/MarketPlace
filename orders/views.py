from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
import requests
from decimal import Decimal
from accounts.decorators import admin_users_forbidden
from .models import Order


@login_required
@admin_users_forbidden
def order_list_view(request):
    if request.user.is_seller:
        orders = Order.objects.filter(
            seller=request.user
        ).select_related('buyer', 'product', 'product__category')
    else:
        orders = Order.objects.filter(
            buyer=request.user
        ).select_related('seller', 'product', 'product__category')
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller', 'product', 'product__category'),
        pk=pk,
    )
    if request.user != order.buyer and request.user != order.seller and not request.user.is_staff:
        messages.error(request, 'You are not authorized to view this order.')
        return redirect('marketplace:home')
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def order_checkout_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller', 'product', 'product__category'),
        pk=pk,
    )
    if request.user != order.buyer:
        messages.error(request, 'You are not authorized to check out this order.')
        return redirect('marketplace:home')
    tax_amount = (order.price_at_purchase * Decimal('0.02')).quantize(Decimal('0.01'))
    grand_total = (order.price_at_purchase + tax_amount).quantize(Decimal('0.01'))
    context = {
        'order': order,
        'deposit_amount': order.deposit_amount,
        'remaining_balance': order.remaining_balance,
        'tax_amount': tax_amount,
        'grand_total': grand_total,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def initiate_khalti_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)

    amount_in_paisa = int(float(order.deposit_amount) * 100)

    payload = {
        "return_url": request.build_absolute_uri(reverse('orders:khalti_verify')),
        "website_url": request.build_absolute_uri('/'),
        "amount": amount_in_paisa,
        "purchase_order_id": str(order.id),
        "purchase_order_name": f"Order #{order.id} Deposit",
        "customer_info": {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email or "test@example.com",
            "phone": "9800000000"
        },
    }

    raw_key = str(getattr(settings, "KHALTI_SECRET_KEY", "")).strip('\'" ')

    if not raw_key:
        raw_key = "Key test_secret_key_f59e8b7d18b4499ca40f68195a846e9b"

    if not raw_key.lower().startswith("key "):
        auth_header = f"Key {raw_key}"
    else:
        auth_header = raw_key

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }

    print("--- OUTGOING KHALTI REQUEST ---")
    print("Headers:", headers)
    print("Payload:", payload)

    try:
        response = requests.post(
            settings.KHALTI_INITIATE_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        messages.error(request, 'Could not reach the Khalti payment gateway. Please try again.')
        return redirect('orders:checkout', pk=order.pk)

    if response.status_code != 200:
        print("--- KHALTI RESPONSE ERROR ---")
        print("Status:", response.status_code)
        print("Body:", response.text)

    if response.status_code == 200 and data.get('pidx') and data.get('payment_url'):
        order.transaction_id = data['pidx']
        order.save()
        return redirect(data['payment_url'])

    messages.error(request, f'Payment initiation failed: {data.get("detail", "Unknown error")}')
    return redirect('orders:checkout', pk=order.pk)


@login_required
def khalti_verify_payment(request):
    pidx = request.GET.get('pidx', '')

    if not pidx:
        messages.error(request, 'Invalid payment response from Khalti.')
        return redirect('orders:order_list')

    raw_key = str(getattr(settings, "KHALTI_SECRET_KEY", "")).strip('\'" ')
    auth_header = raw_key if raw_key.lower().startswith("key ") else f"Key {raw_key}"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            settings.KHALTI_LOOKUP_URL,
            json={'pidx': pidx},
            headers=headers,
            timeout=30,
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        data = {}

    try:
        order = Order.objects.get(transaction_id=pidx, buyer=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'We could not find an order matching this payment.')
        return redirect('orders:order_list')

    if data.get('status') == 'Completed':
        order.amount_paid = order.deposit_amount
        order.payment_type = 'SPLIT_INITIAL'
        order.is_paid = True
        order.save()
        messages.success(
            request,
            f'50% deposit of Rs. {order.amount_paid} received via Khalti. '
            f'The remaining 50% (Rs. {order.remaining_balance}) is due when you receive the product on campus.',
        )
        return redirect('orders:order_detail', pk=order.pk)

    messages.error(request, 'Payment was not completed on Khalti. Please try again.')
    return redirect('orders:checkout', pk=order.pk)
