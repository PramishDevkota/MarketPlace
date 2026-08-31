"""AI-powered Campus Advisor — context-aware product finder.

Uses Google's Gemini model to parse a natural-language student scenario
(e.g. "I am starting BSc Computing Year 1 and have Rs. 5000 budget") into
structured intent, then matches against active inventory and generates a
short AI reasoning tag for every recommended product.
"""

import json
import logging
import re
from decimal import Decimal

from django.conf import settings
from django.db.models import Q

from .models import Product

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-3.6-flash'

_PROGRAMME_LABELS = dict(Product.PROGRAMME_CHOICES)

ADVISOR_PROMPT = (
    'You are a helpful campus shopping advisor for a student marketplace.\n'
    'Parse the following natural-language student scenario into structured '
    'search intent. Extract as much detail as possible:\n'
    '- primary: the main product category or keyword the student needs\n'
    '- related_keywords: 4-6 complementary or related keywords\n'
    '- programme: one of BSC_COMPUTING, BSC_NETWORKING, BSC_MULTIMEDIA, '
    'BBA, OTHER, or null if not mentioned\n'
    '- module_code: e.g. "CS4001" if mentioned, otherwise null\n'
    '- max_budget: the maximum price in NPR if stated, otherwise null\n'
    '- condition: "new", "used", or null if not specified\n'
    '- urgency: any time constraint mentioned (e.g. "this week", "today"), '
    'otherwise null\n\n'
    'Respond with ONLY a JSON object in this exact shape:\n'
    '{\n'
    '  "primary": "<primary keyword>",\n'
    '  "related_keywords": ["<kw1>", "<kw2>", ...],\n'
    '  "programme": "<PROG_CODE or null>",\n'
    '  "module_code": "<CODE or null>",\n'
    '  "max_budget": <number or null>,\n'
    '  "condition": "<new/used/null>",\n'
    '  "urgency": "<text or null>",\n'
    '  "advisor_summary": "<one-sentence friendly summary of what the student needs>"\n'
    '}\n\n'
    'Student scenario: {query}'
)

_REASONING_PROMPT = (
    'You are a campus shopping advisor. For each product listed below, write '
    'a SHORT reasoning tag (max 15 words) explaining WHY it fits the student\'s '
    'scenario. Be specific — reference budget, programme, module, or use-case '
    'when possible.\n\n'
    'Student scenario: {query}\n\n'
    'Products:\n{product_list}\n\n'
    'Respond with ONLY a JSON array of strings, one per product, in the same '
    'order:\n'
    '["<reasoning 1>", "<reasoning 2>", ...]'
)


def _get_genai_model():
    """Return a configured Gemini model instance, or None."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(GEMINI_MODEL)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Could not initialise Gemini: %s', exc)
        return None


def _extract_json(text):
    """Extract and parse the first JSON object or array from *text*."""
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    return None


def _call_gemini(query):
    """Call Gemini to parse the query into structured intent."""
    model = _get_genai_model()
    if model is None:
        return None
    try:
        response = model.generate_content(ADVISOR_PROMPT.format(query=query))
        data = _extract_json(response.text)
        if not data or not isinstance(data, dict):
            return None
        return {
            'primary': str(data.get('primary', query)).strip(),
            'related_keywords': [
                str(k).strip() for k in data.get('related_keywords', []) if k
            ],
            'programme': data.get('programme'),
            'module_code': data.get('module_code'),
            'max_budget': data.get('max_budget'),
            'condition': data.get('condition'),
            'urgency': data.get('urgency'),
            'advisor_summary': str(data.get('advisor_summary', '')).strip(),
        }
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning('Gemini parsing failed (%s); using fallback.', exc)
        return None


def _fallback_parse(query):
    """Local fallback that extracts structured intent without Gemini."""
    lowered = query.lower()
    related = {
        'laptop': ['laptop bag', 'laptop stand', 'mouse', 'sleeve', 'charger'],
        'phone': ['phone case', 'screen protector', 'charger', 'earphones'],
        'headphone': ['earbuds', 'audio jack', 'headphone stand', 'case'],
        'keyboard': ['mouse', 'wrist rest', 'keyboard cover', 'usb hub'],
    }
    primary = query.strip()
    related_kw = []
    for key, keywords in related.items():
        if key in lowered:
            primary = key
            related_kw = keywords
            break

    programme = None
    for code, label in _PROGRAMME_LABELS.items():
        if label.lower() in lowered or code.lower().replace('_', ' ') in lowered:
            programme = code
            break

    module_code = None
    m = re.search(r'\b([A-Z]{2,4}\d{3,4})\b', query, re.IGNORECASE)
    if m:
        module_code = m.group(1).upper()

    budget = None
    bm = re.search(r'(?:rs\.?|npr|budget)\s*[:=]?\s*(\d[\d,]*)', lowered)
    if bm:
        budget = int(bm.group(1).replace(',', ''))

    return {
        'primary': primary,
        'related_keywords': related_kw,
        'programme': programme,
        'module_code': module_code,
        'max_budget': budget,
        'condition': None,
        'urgency': None,
        'advisor_summary': '',
    }


def parse_query(query):
    """Parse a student scenario into structured intent dict."""
    if not query:
        return {'primary': '', 'related_keywords': [], 'advisor_summary': ''}
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


def compute_match_percentage(product, primary, related_keywords, max_budget=None,
                              user=None, programme=None, module_code=None):
    """Compute a 0-100 relevance match percentage for a single product.

    Incorporates primary keyword, related keywords, budget, programme,
    module code, and user purchase history into a weighted score.
    """
    score = 0.0
    base_weight = 5
    related_weight = len(related_keywords) if related_keywords else 0
    # Extra weight for structured signals
    programme_weight = 3 if programme else 0
    module_weight = 3 if module_code else 0
    total_weight = base_weight + related_weight + programme_weight + module_weight

    if total_weight == 0:
        total_weight = 1

    if primary and _term_matches(primary, product):
        score += base_weight
    if related_keywords:
        for kw in related_keywords:
            if _term_matches(kw, product):
                score += 1

    # Programme match bonus
    if programme and product.programme == programme:
        score += programme_weight

    # Module code match bonus
    if module_code and product.module_code and module_code.upper() == product.module_code.upper():
        score += module_weight

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


def _generate_reasoning_tags(query, results):
    """Use Gemini to generate a short AI reasoning tag per product."""
    if not results:
        return []
    model = _get_genai_model()
    if model is None:
        # Fallback: build generic reasoning from structured signals
        return _fallback_reasoning(query, results)

    product_lines = []
    for i, item in enumerate(results):
        p = item['product']
        cat = p.category.name if p.category else 'General'
        product_lines.append(
            f'{i + 1}. {p.name} | Rs. {p.price} | {cat} | '
            f'{p.module_code or "N/A"} | {p.programme or "N/A"}'
        )

    try:
        response = model.generate_content(
            _REASONING_PROMPT.format(
                query=query,
                product_list='\n'.join(product_lines),
            )
        )
        tags = _extract_json(response.text)
        if isinstance(tags, list):
            cleaned = [str(t).strip() for t in tags if t][:len(results)]
            # Pad if short
            while len(cleaned) < len(results):
                cleaned.append('Good match for your search.')
            return cleaned
    except Exception as exc:  # noqa: BLE001
        logger.warning('Gemini reasoning generation failed (%s).', exc)

    return _fallback_reasoning(query, results)


def get_ai_reasoning_tags(query, results):
    """Public helper: generate a short AI reasoning tag per result item.

    ``results`` is a list of dicts each containing a ``product`` key (a
    Product instance). Returns a list of strings aligned to ``results``.
    """
    return _generate_reasoning_tags(query, results)


def _fallback_reasoning(query, results):
    """Build deterministic reasoning tags without Gemini."""
    tags = []
    lowered = query.lower()
    for item in results:
        p = item['product']
        reasons = []
        if p.module_code and p.module_code.lower() in lowered:
            reasons.append(f'Matches {p.module_code} requirement')
        if p.category and p.category.name.lower() in lowered:
            reasons.append(f'In {p.category.name} category')
        if 'budget' in lowered or 'rs' in lowered:
            reasons.append(f'At Rs. {p.price}')
        if not reasons:
            match = item.get('match_percentage')
            if match is not None:
                reasons.append(f'{match}% relevance to your search')
            else:
                reasons.append('Good match for your search')
        tags.append('; '.join(reasons[:2]))
    return tags


def get_personalized_recommendations(user_query, max_budget=None, user=None):
    """Return active inventory ranked by relational relevance to the query.

    Parses the student scenario into structured intent, scores products,
    and generates AI reasoning tags for each recommendation.

    Returns a list sorted by match percentage descending:
    [{"product": <Product>, "match_percentage": 46.7,
      "ai_reasoning": "...", "intent": {...}}, ...]
    """
    if not user_query or not user_query.strip():
        return []

    parsed = parse_query(user_query)
    primary = parsed.get('primary', '')
    related_keywords = parsed.get('related_keywords', [])

    # Budget: prefer explicit param, fall back to parsed value
    effective_budget = max_budget
    if effective_budget is None and parsed.get('max_budget') is not None:
        try:
            effective_budget = float(parsed['max_budget'])
        except (TypeError, ValueError):
            effective_budget = None

    programme = parsed.get('programme')
    module_code = parsed.get('module_code')

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
            max_budget=effective_budget,
            user=user,
            programme=programme,
            module_code=module_code,
        )
        if percentage > 0:
            results.append({
                'product': product,
                'match_percentage': percentage,
            })

    results.sort(key=lambda item: item['match_percentage'], reverse=True)

    # Generate AI reasoning tags
    tags = _generate_reasoning_tags(user_query, results)
    for i, item in enumerate(results):
        item['ai_reasoning'] = tags[i] if i < len(tags) else ''

    # Attach parsed intent so the view/template can display advisor summary
    for item in results:
        item['intent'] = parsed

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
