from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import re
from .models import Product, Category, Cart, CartItem
from .forms import ProductForm, ProductImageFormSet
from .utils import get_recommended_products
from .ai_recommender import (
    recommend_cart_addons,
    parse_query,
    get_ai_reasoning_tags,
)
from accounts.decorators import admin_users_forbidden
from orders.models import Order


def home_view(request):
    approved_products = Product.objects.filter(
        status='APPROVED',
    ).filter(
        Q(is_available=True) | Q(stock=0),
    ).select_related('seller', 'category')[:8]
    categories = Category.objects.filter(is_active=True)[:8]
    context = {
        'products': approved_products,
        'categories': categories,
    }
    return render(request, 'marketplace/home.html', context)


def product_list_view(request):
    products = Product.objects.filter(
        status='APPROVED',
    ).filter(
        Q(is_available=True) | Q(stock=0),
    ).select_related('seller', 'category')

    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    location = request.GET.get('location', '')
    programme = request.GET.get('programme', '')
    module_code = request.GET.get('module_code', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if location:
        products = products.filter(location=location)
    if programme:
        products = products.filter(programme=programme)
    if module_code:
        products = products.filter(module_code__iexact=module_code)
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    categories = Category.objects.filter(is_active=True)
    locations = Product.LOCATION_CHOICES
    programme_choices = Product.PROGRAMME_CHOICES

    context = {
        'products': products,
        'categories': categories,
        'locations': locations,
        'programme_choices': programme_choices,
        'query': query,
        'selected_category': category_slug,
        'selected_location': location,
        'selected_programme': programme,
        'module_code': module_code,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'marketplace/product_list.html', context)


def product_detail_view(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('seller', 'category'),
        pk=pk,
        status__in=['APPROVED', 'SOLD'],
    )
    reviews = product.reviews.select_related('user').all()
    avg_rating = product.average_rating()
    review_count = product.review_count

    user_orders = []
    has_purchased = False
    review_form = None
    if request.user.is_authenticated:
        user_orders = Order.objects.filter(
            buyer=request.user,
            product=product,
        )
        has_purchased = user_orders.filter(is_paid=True).exists()
        if has_purchased and request.user != product.seller:
            from reviews.forms import ReviewForm
            from reviews.models import Review
            existing_review = Review.objects.filter(
                product=product,
                user=request.user,
            ).first()
            review_form = ReviewForm(instance=existing_review)

    recommended_products = get_recommended_products(
        request.user, exclude_product_id=product.pk
    )

    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'user_orders': user_orders,
        'has_purchased': has_purchased,
        'review_form': review_form,
        'recommended_products': recommended_products,
    }
    return render(request, 'marketplace/product_detail.html', context)


@login_required
@admin_users_forbidden
def create_product_view(request):
    if not request.user.is_seller:
        messages.error(request, 'Only approved sellers can add products.')
        return redirect('marketplace:home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.status = 'PENDING'
            product.save()
            image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
            if image_formset.is_valid():
                image_formset.save()
            messages.success(request, 'Product submitted! It will appear on the marketplace once approved by admin.')
            return redirect('seller_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet()

    return render(request, 'marketplace/product_form.html', {'form': form, 'image_formset': image_formset})


@login_required
@admin_users_forbidden
def edit_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
            if image_formset.is_valid():
                image_formset.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('seller_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
        image_formset = ProductImageFormSet(instance=product)
    return render(request, 'marketplace/product_form.html', {'form': form, 'image_formset': image_formset, 'editing': True, 'product': product})


@login_required
@admin_users_forbidden
def delete_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('seller_dashboard')
    return render(request, 'marketplace/product_confirm_delete.html', {'product': product})


@login_required
@admin_users_forbidden
def restock_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        try:
            amount = int(request.POST.get('restock_amount', ''))
        except (TypeError, ValueError):
            amount = 0
        if amount > 0:
            product.stock += amount
            if product.stock > 0:
                product.is_available = True
                product.status = 'APPROVED'
            product.save()
            messages.success(
                request,
                f'Restocked {amount} unit(s). {product.name} now has {product.stock} in stock.',
            )
        else:
            messages.error(request, 'Restock amount must be a positive number.')
        return redirect('seller_dashboard')
    return redirect('seller_dashboard')


@login_required
@admin_users_forbidden
def buy_now_view(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('seller'),
        pk=pk,
        status='APPROVED',
        is_available=True,
    )
    if request.user == product.seller:
        messages.error(request, 'You cannot purchase your own product.')
        return redirect('marketplace:product_detail', pk=product.pk)

    if request.method == 'POST':
        if product.stock <= 0:
            messages.error(request, 'Sorry, this product is sold out.')
            return redirect('marketplace:product_detail', pk=product.pk)

        try:
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (TypeError, ValueError):
            quantity = 1
        if quantity > product.stock:
            messages.error(request, f'Only {product.stock} unit(s) available for this product.')
            return redirect('marketplace:product_detail', pk=product.pk)

        order = Order.objects.create(
            buyer=request.user,
            seller=product.seller,
            product=product,
            price_at_purchase=product.price,
            quantity=quantity,
            meetup_location=request.POST.get('meetup_location', 'BLOCK_A_HALLWAY'),
            meetup_time_notes=request.POST.get('meetup_time_notes', ''),
            status='PENDING',
        )
        messages.success(
            request,
            f'Order #{order.pk} created. Complete the Rs. {order.deposit_amount} advance '
            f'deposit to reserve your product.',
        )
        return redirect('orders:checkout', pk=order.pk)

    return render(request, 'marketplace/buy_confirm.html', {'product': product})


@csrf_exempt
@require_POST
def add_to_cart(request, product_id):
    """Add a product to the user's cart (or a guest session cart)."""
    product = get_object_or_404(
        Product.objects.select_related('seller', 'category'),
        pk=product_id,
        status='APPROVED',
        is_available=True,
    )

    try:
        data = request.POST.copy()
        if request.content_type and 'application/json' in request.content_type:
            import json as _json
            data = _json.loads(request.body or '{}')
    except (ValueError, TypeError):
        data = request.POST or {}

    try:
        quantity = int(data.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    if quantity < 1:
        quantity = 1

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity},
    )
    if not created:
        item.quantity += quantity
        item.save()

    addons = recommend_cart_addons(product)

    recommended_products = []
    for rec_product in addons['recommendations']:
        recommended_products.append({
            'id': rec_product.pk,
            'name': rec_product.name,
            'price': str(rec_product.price),
            'image': rec_product.image.url if rec_product.image else None,
            'product_url': rec_product.get_absolute_url(),
        })

    return JsonResponse({
        'status': 'ok',
        'cart_count': cart.items.aggregate(total=Sum('quantity'))['total'] or 0,
        'cart_total': str(cart.total_price),
        'added_item': {
            'id': product.pk,
            'name': product.name,
            'price': str(product.price),
            'quantity': item.quantity,
            'subtotal': str(item.subtotal),
        },
        'recommendations': recommended_products,
        'recommendation_message': addons['message'],
    })


def _get_or_create_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.get_or_create(user=request.user)[0]
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    return Cart.objects.get_or_create(session_key=session_key)[0]


def cart_view(request):
    """Display the user's cart contents with per-item purchase links."""
    cart = None
    items = []
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()

    if cart:
        items = cart.items.select_related('product', 'product__seller', 'product__category').all()

    context = {
        'cart': cart,
        'items': items,
    }
    return render(request, 'marketplace/cart.html', context)


@require_POST
def update_cart_item_view(request, item_id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = item.quantity
    if quantity < 1:
        quantity = 1

    product = item.product
    if quantity > product.stock:
        messages.error(request, f'Only {product.stock} unit(s) available for "{product.name}".')
        return redirect('marketplace:cart')

    item.quantity = quantity
    item.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        return JsonResponse({
            'status': 'ok',
            'quantity': item.quantity,
            'subtotal': str(item.subtotal),
            'cart_total': str(cart.total_price),
            'cart_count': cart.items.aggregate(total=Sum('quantity'))['total'] or 0,
        })
    return redirect('marketplace:cart')


@require_POST
def remove_cart_item_view(request, item_id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    product_name = item.product.name
    item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        return JsonResponse({
            'status': 'ok',
            'removed': True,
            'product_name': product_name,
            'cart_total': str(cart.total_price),
            'cart_count': cart.items.aggregate(total=Sum('quantity'))['total'] or 0,
        })
    messages.success(request, f'Removed "{product_name}" from your cart.')
    return redirect('marketplace:cart')


@login_required
@admin_users_forbidden
def seller_dashboard_view(request):
    if not request.user.is_seller:
        messages.error(request, 'Seller access required.')
        return redirect('marketplace:home')

    products = Product.objects.filter(
        seller=request.user
    ).select_related('category')

    total_products = products.count()
    approved_products = products.filter(status='APPROVED').count()
    pending_products = products.filter(status='PENDING').count()
    rejected_products = products.filter(status='REJECTED').count()
    sold_products = products.filter(status='SOLD').count()

    orders = Order.objects.filter(
        seller=request.user
    ).select_related('buyer', 'product')
    total_revenue = orders.filter(
        status__in=['CONFIRMED', 'COMPLETED']
    ).aggregate(total=Sum('price_at_purchase'))['total'] or 0

    incoming_orders = orders.exclude(status='CANCELLED')[:10]

    context = {
        'products': products,
        'total_products': total_products,
        'approved_products': approved_products,
        'pending_products': pending_products,
        'rejected_products': rejected_products,
        'sold_products': sold_products,
        'total_revenue': total_revenue,
        'incoming_orders': incoming_orders,
    }
    return render(request, 'marketplace/seller_dashboard.html', context)


@login_required
@admin_users_forbidden
def buyer_dashboard_view(request):
    orders = Order.objects.filter(
        buyer=request.user
    ).select_related('seller', 'product', 'product__category')

    total_purchases = orders.count()
    active_orders = orders.filter(status__in=['PENDING', 'CONFIRMED']).count()
    completed_orders = orders.filter(status='COMPLETED').count()
    total_spent = orders.filter(
        status__in=['CONFIRMED', 'COMPLETED']
    ).aggregate(total=Sum('price_at_purchase'))['total'] or 0

    from messaging.models import Conversation
    active_chats = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related('buyer', 'seller', 'product').distinct()

    from reviews.models import Review
    completed_product_ids = orders.filter(
        status='COMPLETED'
    ).values_list('product_id', flat=True)
    reviewed_product_ids = Review.objects.filter(
        user=request.user,
        product_id__in=completed_product_ids
    ).values_list('product_id', flat=True)
    pending_review_products = Product.objects.filter(
        id__in=completed_product_ids
    ).exclude(id__in=reviewed_product_ids)

    recommended_products = get_recommended_products(request.user)

    context = {
        'orders': orders,
        'total_purchases': total_purchases,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
        'active_chats': active_chats,
        'pending_review_products': pending_review_products,
        'recommended_products': recommended_products,
    }
    return render(request, 'marketplace/buyer_dashboard.html', context)


def marketplace_overview(request):
    """Public marketplace dashboard with marketplace-wide sales insights."""
    from django.db.models import Sum, Count

    active_orders = Order.objects.exclude(status='CANCELLED')

    total_items_sold = active_orders.count()
    total_gmv = active_orders.aggregate(total=Sum('price_at_purchase'))['total'] or 0

    top_categories = (
        active_orders
        .values('product__category__name')
        .annotate(
            items_sold=Count('id'),
            gmv=Sum('price_at_purchase'),
        )
        .filter(product__category__isnull=False)
        .order_by('-items_sold')[:5]
    )

    recent_orders = (
        active_orders
        .select_related('buyer', 'product', 'product__category')
        .order_by('-created_at')[:10]
    )

    context = {
        'total_items_sold': total_items_sold,
        'total_gmv': total_gmv,
        'top_categories': top_categories,
        'recent_orders': recent_orders,
    }
    return render(request, 'marketplace/overview.html', context)


def about_view(request):
    return render(request, 'pages/about.html')


def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if name and email and subject and message_text:
            from django.core.mail import send_mail
            from django.conf import settings

            full_subject = f"[Islington Marketplace] {subject}"
            full_message = f"From: {name} <{email}>\n\n{message_text}"
            send_mail(
                full_subject,
                full_message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else email,
                [settings.DEFAULT_FROM_EMAIL] if hasattr(settings, 'DEFAULT_FROM_EMAIL') else [],
                fail_silently=True,
            )
            messages.success(request, 'Your message has been sent successfully!')
        else:
            messages.error(request, 'Please fill in all fields.')

    return render(request, 'pages/contact.html')


_COMMON_FILLER_WORDS = {
    'i', 'want', 'need', 'some', 'a', 'an', 'for', 'the', 'to', 'of', 'and',
    'or', 'with', 'my', 'me', 'looking', 'find', 'buy', 'have',
    'can', 'you', 'help', 'give', 'new', 'used',
    'product', 'item', 'things', 'stuff', 'campus', 'islington', 'college',
    'university', 'year', 'semester', 'under', 'around', 'about', 'npr', 'rs',
    'budget', 'any', 'where', 'how', 'much', 'price',
}

_SYNONYMS = {
    'bag': ['bag', 'backpack', 'rucksack', 'bagpack', 'satchel', 'knapsack',
            'schoolbag', 'laptop bag', 'carry bag'],
    'notebook': ['notebook', 'notepad', 'note book', 'writing pad',
                 'exercise book'],
    'book': ['book', 'textbook', 'novel', 'reading', 'books'],
    'electronics': ['electronics', 'electronic', 'gadget', 'gadgets',
                    'device', 'devices', 'tech', 'accessory', 'accessories'],
    'laptop': ['laptop', 'notebook computer', 'computer'],
    'pen': ['pen', 'pens', 'stationery'],
    'charger': ['charger', 'charging cable', 'power adapter'],
    'headphone': ['headphone', 'headphones', 'earphone', 'earphones',
                  'earbuds', 'audio'],
    'keyboard': ['keyboard', 'key board'],
    'mouse': ['mouse', 'computer mouse'],
    'phone': ['phone', 'mobile', 'smartphone'],
    'shoes': ['shoes', 'shoe', 'footwear', 'sneakers'],
    'shirt': ['shirt', 'shirts', 'tops'],
}


def _extract_core_keywords(query):
    """Pull meaningful search terms out of a natural-language prompt.

    Converts e.g. "I want some bags" into the key term "bag" (singularised)
    and drops filler/stop words.
    """
    if not query:
        return []
    words = re.split(r'[^a-zA-Z0-9]+', query.lower())
    core = []
    for word in words:
        word = word.strip()
        # Drop plurals ("bags" -> "bag", "notebooks" -> "notebook")
        if word.endswith('ies') and len(word) > 4:
            word = word[:-3] + 'y'
        elif word.endswith('es') and len(word) > 4:
            word = word[:-2]
        elif word.endswith('s') and len(word) > 3 and not word.endswith('ss'):
            word = word[:-1]
        if word and word not in _COMMON_FILLER_WORDS and len(word) >= 3:
            if word not in core:
                core.append(word)
    return core


def _expand_synonyms(keywords):
    """Return the original keywords plus any synonyms for them."""
    expanded = list(keywords)
    for kw in keywords:
        for base, synonyms in _SYNONYMS.items():
            if kw == base or kw in synonyms:
                for syn in synonyms:
                    if syn not in expanded:
                        expanded.append(syn)
    return expanded


def _search_products(query):
    """Match products against a natural-language query across broad fields.

    Builds a multi-field OR query (title, description, category, programme,
    module code) so both academic ("BSc Computing Year 1 books") and general
    ("bags", "electronics") searches work.
    """
    terms = _extract_core_keywords(query)
    if not terms:
        return Product.objects.none()

    expanded = _expand_synonyms(terms)

    q = Q()
    for term in expanded:
        q |= (
            Q(name__icontains=term) |
            Q(description__icontains=term) |
            Q(category__name__icontains=term) |
            Q(programme__icontains=term) |
            Q(module_code__icontains=term)
        )

    # Multi-word academic phrases (e.g. "BSc Computing") should also match the
    # programme / module fields as a unit.
    lowered = query.lower()
    for code, label in dict(Product.PROGRAMME_CHOICES).items():
        if label.lower() in lowered or code.lower().replace('_', ' ') in lowered:
            q |= Q(programme__icontains=code)

    return Product.objects.filter(
        q
    ).filter(
        status='APPROVED',
        is_available=True,
    ).select_related('seller', 'category').distinct()


def ai_product_finder_view(request):
    """Render the AI Campus Advisor.

    Accepts a natural-language ``query`` and optional ``max_budget`` via GET.
    Parses the scenario into structured intent, matches against active
    inventory using a flexible multi-field search, generates AI reasoning
    tags, and renders an advisor-style conversational UI.

    Handles both academic prompts (e.g. "BSc Computing Year 1 books") and
    broad general prompts (e.g. "bags", "electronics"). If nothing matches,
    falls back to the most recent listings as suggested items.
    """
    query = request.GET.get('query', '').strip()
    max_budget_raw = request.GET.get('max_budget', '').strip()

    max_budget = None
    try:
        if max_budget_raw:
            max_budget = float(max_budget_raw)
    except ValueError:
        max_budget = None

    recommendations = None
    advisor_summary = ''
    intent = {}
    message = ''

    if query:
        # Fallback-friendly flexible product search that works for both
        # academic and broad general queries.
        products = _search_products(query)

        # Reuse parsed intent to enrich results with AI reasoning whenever
        # Gemini (or the local fallback) produces structured signals.
        parsed = parse_query(query)
        intent = parsed
        advisor_summary = parsed.get('advisor_summary', '')

        if products.exists():
            recommendations = []
            for product in products[:20]:
                recommendations.append({
                    'product': product,
                    'intent': parsed,
                    'match_percentage': None,
                })
            tags = get_ai_reasoning_tags(query, recommendations)
            for i, item in enumerate(recommendations):
                item['ai_reasoning'] = tags[i] if i < len(tags) else ''
        else:
            # Empty-results fallback: show recent listings instead of a blank page.
            recent = Product.objects.filter(
                status='APPROVED',
                is_available=True,
            ).select_related('seller', 'category')[:4]
            recommendations = [
                {'product': product, 'intent': parsed, 'match_percentage': None}
                for product in recent
            ]
            message = (
                f"No exact matches found for '{query}', but here are some "
                "recent listings on campus!"
            )
    else:
        # No query yet: show the most recent listings as a friendly starting point.
        recent = Product.objects.filter(
            status='APPROVED',
            is_available=True,
        ).select_related('seller', 'category')[:4]
        recommendations = [
            {'product': product, 'intent': {}, 'match_percentage': None}
            for product in recent
        ]
        message = 'Try describing what you are looking for, e.g. "bags" or "BSc Computing Year 1 books".'

    context = {
        'query': query,
        'max_budget': max_budget,
        'recommendations': recommendations,
        'advisor_summary': advisor_summary,
        'intent': intent,
        'message': message,
    }
    return render(request, 'marketplace/ai_finder.html', context)
