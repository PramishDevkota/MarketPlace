"""AI-powered relational product finder.

Uses Google's Gemini model to parse a free-text user query into a primary
category and a set of complementary/related keywords, then matches those
against active inventory to produce a relevance score (0% - 100%) for each
product.
"""

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.db.models import Q

from .models import Product

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.5-flash'

_PROMPT = (
    'You are a helpful shopping assistant for an online marketplace.\n'
    'Parse the following user product query into a primary category and a list '
    'of related complementary keywords (e.g. accessories, add-ons or products '
    'people typically buy together with the primary item).\n'
    'Respond with ONLY a JSON object in this exact shape:\n'
    '{"primary": "<primary category keyword>", '
    '"related_keywords": ["<keyword 1>", "<keyword 2>"]}\n'
    'Include 4 to 6 related keywords that would make useful relational finds.\n\n'
    'User query: {query}'
)


def _call_gemini(query):
    """Call Gemini to parse the query, returning a dict with key handling."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        logger.info('No GEMINI_API_KEY configured; falling back to keyword matching.')
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(_PROMPT.format(query=query))
        text = response.text.strip()
        text = text[text.index('{'):text.rindex('}') + 1]
        data = json.loads(text)
        return {
            'primary': str(data.get('primary', query)).strip(),
            'related_keywords': [
                str(k).strip() for k in data.get('related_keywords', []) if k
            ],
        }
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning('Gemini parsing failed (%s); using fallback.', exc)
        return None


def _fallback_parse(query):
    """Simple local fallback parse when Gemini is unavailable."""
    related = {
        'laptop': ['laptop bag', 'laptop stand', 'mouse', 'sleeve', 'charger'],
        'phone': ['phone case', 'screen protector', 'charger', 'earphones'],
        'headphone': ['earbuds', 'audio jack', 'headphone stand', 'case'],
        'keyboard': ['mouse', 'wrist rest', 'keyboard cover', 'usb hub'],
    }
    lowered = query.lower()
    primary = query.strip()
    for key, keywords in related.items():
        if key in lowered:
            primary = key
            return {'primary': primary, 'related_keywords': keywords}
    return {'primary': primary, 'related_keywords': []}


def parse_query(query):
    """Parse a user query into primary + related keywords."""
    if not query:
        return {'primary': '', 'related_keywords': []}
    parsed = _call_gemini(query)
    if parsed:
        return parsed
    return _fallback_parse(query)


def _term_matches(term, product):
    """True if the term appears in the product title or category name."""
    term = term.lower()
    if term in product.name.lower():
        return True
    if product.category and term in product.category.name.lower():
        return True
    return False


def _purchased_keywords(user):
    """Collect normalized keywords from a user's purchase history."""
    keywords = []
    if not (user and user.is_authenticated):
        return keywords
    try:
        from orders.models import Order

        products = Product.objects.filter(
            orders__buyer=user,
        ).filter(
            Q(status='SOLD') | Q(status='APPROVED'),
        ).select_related('category').distinct()
        for product in products:
            keywords.extend(product.name.lower().split())
            if product.category:
                keywords.append(product.category.name.lower())
    except Exception as exc:  # noqa: BLE001
        logger.warning('Could not load purchase history: %s', exc)
    return set(keywords)


def compute_match_percentage(product, primary, related_keywords, max_budget=None, user=None):
    """Compute a 0-100 relevance match percentage for a single product."""
    score = 0.0
    total_weight = 5 + len(related_keywords) if related_keywords else 5

    if primary and _term_matches(primary, product):
        score += 5
    if related_keywords:
        for kw in related_keywords:
            if _term_matches(kw, product):
                score += 1

    if max_budget is not None:
        budget = Decimal(str(max_budget))
        if product.price <= budget:
            score += 2
        else:
            score -= 2

    if user is not None and user.is_authenticated:
        purchased = _purchased_keywords(user)
        if purchased:
            product_terms = set(product.name.lower().split())
            if product.category:
                product_terms.add(product.category.name.lower())
            if product_terms & purchased:
                score += 1

    percentage = max(0.0, min(100.0, (score / total_weight) * 100.0))
    return round(percentage, 1)


def get_personalized_recommendations(user_query, max_budget=None, user=None):
    """Return active inventory ranked by relational relevance to the query.

    Returns a list sorted by match percentage descending:
    [{"product": <Product>, "match_percentage": 46.7}, ...]
    """
    if not user_query or not user_query.strip():
        return []

    parsed = parse_query(user_query)
    primary = parsed.get('primary', '')
    related_keywords = parsed.get('related_keywords', [])

    products = Product.objects.filter(
        status='APPROVED',
        is_available=True,
    ).select_related('seller', 'category')

    results = []
    for product in products:
        percentage = compute_match_percentage(
            product,
            primary,
            related_keywords,
            max_budget=max_budget,
            user=user,
        )
        if percentage > 0:
            results.append({
                'product': product,
                'match_percentage': percentage,
            })

    results.sort(key=lambda item: item['match_percentage'], reverse=True)
    return results


_GEMINI_MODEL_ADDONS = GEMINI_MODEL

_ADDONS_PROMPT = (
    'You are a shopping assistant on an online marketplace.\n'
    'A shopper just added the following product to their cart:\n'
    '"{product_name}" (category: {category})\n'
    'Recommend up to 3 complementary products that people typically buy '
    'together with this item (e.g. adding "Laptop" would suggest "Mouse", '
    '"Laptop Stand", or "Laptop Bag").\n'
    'Respond ONLY with a JSON object in this exact shape:\n'
    '{"message": "<a short friendly recommendation message>", '
    '"terms": ["<product term 1>", "<product term 2>", "<product term 3>"]}\n'
    'Each term should be a short product keyword that we will match against our '
    'inventory. Use at most 3 terms.'
)

_FALLBACK_ADDONS = {
    'laptop': (['laptop bag', 'laptop stand', 'mouse'], 'Complete your setup with these laptop essentials.'),
    'mouse': (['keyboard', 'mouse pad', 'usb hub'], 'Pair these with your mouse for a better desk setup.'),
    'keyboard': (['mouse', 'keyboard cover', 'wrist rest'], 'Round out your workstation with these accessories.'),
    'phone': (['phone case', 'screen protector', 'earphones'], 'Protect and enhance your phone with these.'),
    'headphone': (['earbuds', 'headphone stand', 'audio jack'], 'Upgrade your audio experience with these picks.'),
    'charger': (['cable', 'power bank', 'charger'], 'Keep your devices powered with these add-ons.'),
    'bag': (['wallet', 'bottle', 'pouch'], 'Carry your essentials in style with these accessories.'),
    'book': (['bookmark', 'notebook', 'pen'], 'Stock up on stationery to go with your reading.'),
}


def _parse_addons_response(text):
    """Extract message + terms from Gemini's JSON response."""
    try:
        text = text.strip()
        text = text[text.index('{'):text.rindex('}') + 1]
        data = json.loads(text)
        message = str(data.get('message', '')).strip()
        terms = [
            str(t).strip()
            for t in data.get('terms', []) if t
        ][:3]
        return message, terms
    except Exception as exc:  # noqa: BLE001
        logger.warning('Gemini add-ons parsing failed (%s).', exc)
        return '', []


def recommend_cart_addons(product, limit=3):
    """Recommend up to `limit` complementary products for a cart add-on.

    Queries the active inventory (excluding `product`), asks Gemini
    (gemini-2.5-flash) to pick complementary ecosystem products, and returns
    a dict with the matching Product querysets plus a recommendation message.

    Returns:
        {"recommendations": [<Product>, ...], "message": "<str>"}
    """
    if product is None:
        return {'recommendations': [], 'message': ''}

    active = Product.objects.filter(
        status='APPROVED',
        is_available=True,
    ).exclude(pk=product.pk).select_related('seller', 'category')

    category = product.category.name if product.category else 'General'
    message = ''
    terms = []

    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(_GEMINI_MODEL_ADDONS)
            response = model.generate_content(
                _ADDONS_PROMPT.format(
                    product_name=product.name,
                    category=category,
                )
            )
            if response:
                message, terms = _parse_addons_response(response.text)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Gemini add-ons call failed (%s); using fallback.', exc)

    if not terms:
        lowered = product.name.lower()
        keywords = []
        for fallback_key, (fallback_terms, fallback_msg) in _FALLBACK_ADDONS.items():
            if fallback_key in lowered or (
                product.category and fallback_key in product.category.name.lower()
            ):
                keywords = fallback_terms
                message = fallback_msg
                break
        terms = keywords

    if not terms:
        return {'recommendations': [], 'message': message}

    matching = []
    for term in terms:
        term = term.lower().strip()
        if not term:
            continue
        q = active.filter(
            Q(name__icontains=term) |
            Q(category__name__icontains=term)
        )
        for matched in q[:2]:
            if matched not in matching:
                matching.append(matched)

    recommendations = matching[:limit]
    if not message:
        message = 'You might also like these complementary products.'

    return {
        'recommendations': recommendations,
        'message': message,
    }
