from django.db.models import Q
from .models import Product
from orders.models import Order


def get_recommended_products(user, exclude_product_id=None, limit=8):
    """Analyze a buyer's order history to suggest relevant available products.

    Finds available products from categories the user has purchased from
    (e.g., accessories or items in the same category as past purchases),
    excluding products the user has already ordered.
    """
    if not user.is_authenticated:
        return Product.objects.none()

    purchased_category_ids = Order.objects.filter(
        buyer=user,
    ).values_list(
        'product__category_id', flat=True
    ).distinct()

    purchased_product_ids = Order.objects.filter(
        buyer=user,
    ).values_list(
        'product_id', flat=True
    )

    exclude_ids = set(purchased_product_ids)
    if exclude_product_id is not None:
        exclude_ids.add(exclude_product_id)

    recommended = Product.objects.filter(
        status='APPROVED',
        is_available=True,
        category_id__in=purchased_category_ids,
    ).exclude(
        id__in=exclude_ids,
    ).select_related('seller', 'category').order_by('-created_at')[:limit]

    return recommended
