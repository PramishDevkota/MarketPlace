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
    """'My Orders': every order where the current user is the buyer."""
    orders = Order.objects.filter(
        buyer=request.user
    ).select_related('seller', 'product', 'product__category')
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
@admin_users_forbidden
def sales_list_view(request):
    """'My Sales': every order placed against products owned by the current user."""
    orders = Order.objects.filter(
        seller=request.user
    ).select_related('buyer', 'product', 'product__category')
    context = {
        'orders': orders,
    }
    return render(request, 'orders/sales_list.html', context)


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

    total_price = order.total_price
    deposit_amount = order.deposit_amount
    remaining_amount = order.remaining_amount

    if not order.is_paid and order.status != 'PENDING':
        order.status = 'PENDING'
        order.save()

    tax_amount = (total_price * Decimal('0.02')).quantize(Decimal('0.01'))
    grand_total = (total_price + tax_amount).quantize(Decimal('0.01'))
    context = {
        'order': order,
        'total_price': total_price,
        'deposit_amount': deposit_amount,
        'remaining_balance': remaining_amount,
        'tax_amount': tax_amount,
        'grand_total': grand_total,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_cancel_view(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.user != order.buyer:
        messages.error(request, 'You are not authorized to cancel this order.')
        return redirect('marketplace:home')

    if order.status != 'PENDING' or order.is_paid:
        messages.error(request, 'This order can no longer be cancelled. Orders can only be cancelled before payment is made.')
        return redirect('orders:order_detail', pk=order.pk)

    order.status = 'CANCELLED'
    order.save()

    messages.success(request, f'Order #{order.pk} has been cancelled.')
    return redirect('orders:order_detail', pk=order.pk)


@login_required
def order_success_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller', 'product', 'product__category'),
        pk=pk,
    )
    if request.user != order.buyer and request.user != order.seller and not request.user.is_staff:
        messages.error(request, 'You are not authorized to view this order.')
        return redirect('marketplace:home')
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def initiate_khalti_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)

    if order.is_paid or order.status in ('PAID', 'COMPLETED'):
        messages.info(request, f'Order #{order.pk} has already been paid.')
        return redirect('orders:order_detail', pk=order.pk)

    amount_in_paisa = int(float(order.deposit_amount) * 100)

    payload = {
        "return_url": request.build_absolute_uri(reverse('orders:khalti_verify')),
        "website_url": request.build_absolute_uri('/'),
        "amount": amount_in_paisa,
        "purchase_order_id": str(order.id),
        "purchase_order_name": f"Order #{order.id} Advance Deposit",
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

    if order.is_paid or order.status in ('PAID', 'COMPLETED'):
        messages.info(request, f'Order #{order.pk} has already been paid. The stock was already reserved.')
        return redirect('orders:order_detail', pk=order.pk)

    if data.get('status') == 'Completed':
        order.amount_paid = order.deposit_amount
        order.payment_type = 'SPLIT_INITIAL'
        order.is_paid = True
        order.status = 'COMPLETED'
        order.save()

        product = order.product
        product.stock -= order.quantity
        if product.stock <= 0:
            product.stock = 0
            product.is_available = False
        product.save()

        messages.success(
            request,
            f'Advance deposit of Rs. {order.amount_paid} received via Khalti. '
            f'The remaining balance of Rs. {order.remaining_amount} is due when you receive '
            f'the {product.name} on campus.',
        )
        return redirect(f"{reverse('marketplace:product_detail', kwargs={'pk': order.product.pk})}?payment=success#review-section")

    messages.error(request, 'Payment was not completed on Khalti. Your stock was not reserved. Please try again.')
    return redirect('orders:checkout', pk=order.pk)
