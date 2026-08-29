from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from marketplace.models import Product
from orders.models import Order
from accounts.decorators import admin_users_forbidden
from .models import Review
from .forms import ReviewForm


@login_required
@admin_users_forbidden
def add_review(request, order_id):
    """Allow a buyer to rate and review a completed order."""
    order = get_object_or_404(
        Order.objects.select_related('product', 'buyer'),
        pk=order_id,
        buyer=request.user,
        status='COMPLETED',
    )

    existing_review = Review.objects.filter(
        product=order.product,
        user=request.user,
        order=order,
    ).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = order.product
            review.user = request.user
            review.order = order
            review.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('marketplace:product_detail', pk=order.product.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReviewForm(instance=existing_review)

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

    order = Order.objects.filter(
        buyer=request.user,
        product=product,
        status='COMPLETED',
    ).first()

    if not order:
        messages.error(request, 'You can only review products you have purchased.')
        return redirect('marketplace:product_detail', pk=product.pk)

    existing_review = Review.objects.filter(
        product=product,
        user=request.user,
        order=order,
    ).first()

    if existing_review:
        messages.info(request, 'You have already reviewed this product.')
        return redirect('marketplace:product_detail', pk=product.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.order = order
            review.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('marketplace:product_detail', pk=product.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReviewForm()

    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'reviews/review_form.html', context)
