from django.db.models import Q

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from marketplace.models import Product
from orders.models import Order
from accounts.decorators import admin_users_forbidden
from .models import Review
from .forms import ReviewForm


def _qualifying_orders(user, product=None):
    """Return orders the user may review.

    A buyer may review a product once they have paid for it (``is_paid``) or
    once the order has reached the PAID/COMPLETED state (covers both the
    deposit-paid and fully delivered flows).
    """
    orders = Order.objects.filter(buyer=user).filter(
        Q(is_paid=True) | Q(status__in=['PAID', 'COMPLETED'])
    )
    if product is not None:
        orders = orders.filter(product=product)
    return orders


def _handle_review_submission(request, product, order):
    """Shared create/update logic for a single (product, user, order) review.

    Always returns a ``(redirect_or_None, form)`` tuple so callers can unpack
    it consistently.
    """
    existing_review = Review.objects.filter(
        product=product,
        user=request.user,
        order=order,
    ).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.order = order
            review.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('marketplace:product_detail', pk=product.pk), None
        messages.error(request, 'Please correct the errors below.')
        return None, form
    form = ReviewForm(instance=existing_review)
    return None, form


@login_required
@admin_users_forbidden
def add_review(request, order_id):
    """Allow a buyer to rate and review a paid/completed order."""
    order = get_object_or_404(
        Order.objects.select_related('product', 'buyer'),
        pk=order_id,
        buyer=request.user,
    )

    orders = _qualifying_orders(request.user)
    if not orders.filter(pk=order.pk).exists():
        messages.error(request, 'You can only review products you have purchased.')
        return redirect('orders:order_detail', pk=order.pk)

    existing_review = Review.objects.filter(
        product=order.product,
        user=request.user,
        order=order,
    ).first()
    if existing_review:
        messages.info(request, 'You have already reviewed this product.')
        return redirect('orders:order_detail', pk=order.pk)

    result, form = _handle_review_submission(request, order.product, order)
    if result:
        return result

    context = {
        'form': form,
        'product': order.product,
        'order': order,
    }
    return render(request, 'reviews/review_form.html', context)


@login_required
@admin_users_forbidden
def create_review_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, status='APPROVED')

    order = _qualifying_orders(request.user, product=product).first()

    if not order:
        messages.error(request, 'You can only review products you have purchased.')
        return redirect('marketplace:product_detail', pk=product.pk)

    existing_review = Review.objects.filter(
        product=product,
        user=request.user,
    ).first()

    if existing_review:
        messages.info(request, 'You have already reviewed this product.')
        return redirect('marketplace:product_detail', pk=product.pk)

    result, form = _handle_review_submission(request, product, order)
    if result:
        return result

    context = {
        'form': form,
        'product': product,
        'order': order,
    }
    return render(request, 'reviews/review_form.html', context)
