import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q, Avg
from django.urls import reverse

from .models import Product, Category
from .services.gemini_service import analyze_user_voice_query

logger = logging.getLogger(__name__)

# Category mapping to UniMart database Category slugs
CATEGORY_SLUG_MAP = {
    "clothing": ["cloote", "men-collections"],
    "electronic_item": ["electronic-item"],
    "gaming": ["electronic-item"],
    "men_collections": ["men-collections"],
    "food": ["food"],
    "grocery": ["grocery"],
    "toys": ["toy"],
}

BN_DIGITS = {
    "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
    "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯"
}


def to_bn_digits(number: int) -> str:
    """Converts English digits to Bengali digits."""
    return "".join(BN_DIGITS.get(ch, ch) for ch in str(number))


def get_client_ip(request) -> str:
    """Extracts client IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@csrf_exempt
@require_POST
def voice_assistant_api(request):
    """
    Voice Assistant API Endpoint:
    Receives JSON: {"text": "..."}
    Sends to Gemini Function Calling -> queries DB -> returns Bengali spoken reply and product cards.
    """
    # 1. Rate Limiting Check (20 requests per minute per IP)
    client_ip = get_client_ip(request)
    rate_key = f"voice_assist_rate_{client_ip}"
    request_count = cache.get(rate_key, 0)
    if request_count >= 20:
        return JsonResponse({
            "reply": "অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করে আবার বলুন।",
            "products": [],
            "status": "rate_limited"
        }, status=429)
    cache.set(rate_key, request_count + 1, timeout=60)

    # 2. Parse JSON Request
    try:
        body = json.loads(request.body.decode("utf-8"))
        user_text = (body.get("text") or "").strip()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            "reply": "বুঝতে পারিনি, আবার বলুন।",
            "products": [],
            "status": "invalid_json"
        }, status=400)

    if not user_text:
        return JsonResponse({
            "reply": "বুঝতে পারিনি, আবার বলুন।",
            "products": [],
            "status": "empty_text"
        })

    # 3. Call Gemini Function Calling Service
    gemini_result = analyze_user_voice_query(user_text)
    fn_name = gemini_result.get("function_name")
    fn_args = gemini_result.get("args") or {}
    error = gemini_result.get("error")

    if error:
        logger.warning("Voice assistant Gemini error: %s", error)

    # Fallback when no function was called by Gemini or an error occurred
    if not fn_name:
        fallback_reply = "বুঝতে পারিনি, আবার বলুন।"
        if error == "API_KEY_NOT_CONFIGURED":
            fallback_reply = "API কী সেট করা হয়নি। অনুগ্রহ করে .env ফাইলে GEMINI_API_KEY দিন।"

        return JsonResponse({
            "reply": fallback_reply,
            "products": [],
            "action": None,
            "debug_error": error if settings.DEBUG else None
        })


    # 4. Execute Read-Only Database Queries Based on Selected Function
    products_qs = Product.objects.none()
    condition_applied = None
    rating_applied = None

    try:
        user_lower = user_text.lower()

        if fn_name == "show_offers":
            # Query products with is_offer=True
            products_qs = Product.objects.filter(is_offer=True).annotate(
                avg_rating=Avg("rating__rating")
            ).order_by("-id")

        elif fn_name == "show_products":
            products_qs = Product.objects.annotate(
                avg_rating=Avg("rating__rating")
            )

            category_arg = (fn_args.get("category") or "").strip().lower()
            subcategory_arg = (fn_args.get("subcategory") or "").strip()
            search_text_arg = (fn_args.get("search_text") or "").strip()
            condition_arg = (fn_args.get("condition") or "").strip().lower()
            min_rating_arg = fn_args.get("min_rating")

            # Heuristic boosting for condition (ensures instant 100% accuracy)
            if not condition_arg:
                if any(w in user_lower for w in ["নতুন", "new", "ব্র্যান্ড নিউ", "brand new"]):
                    condition_arg = "new"
                elif any(w in user_lower for w in ["ব্যবহৃত", "পুরাতন", "used", "সেকেন্ড হ্যান্ড", "সেকেন্ডহ্যান্ড", "second hand"]):
                    condition_arg = "used"

            # Heuristic boosting for rating
            if not min_rating_arg:
                if any(w in user_lower for w in ["টপ রেটেড", "ভালো রেটিং", "টপ রেটিং", "top rated"]):
                    min_rating_arg = 4
                elif "৫ স্টার" in user_lower or "5 star" in user_lower:
                    min_rating_arg = 5
                elif "৪ স্টার" in user_lower or "4 star" in user_lower:
                    min_rating_arg = 4

            # Filter by Condition (new vs used)
            if condition_arg in ("new", "used"):
                products_qs = products_qs.filter(condition=condition_arg)
                condition_applied = condition_arg

            # Filter by Rating
            if min_rating_arg:
                try:
                    r_val = float(min_rating_arg)
                    products_qs = products_qs.filter(avg_rating__gte=r_val)
                    rating_applied = r_val
                except (ValueError, TypeError):
                    pass

            # Filter by Category
            if category_arg:
                if category_arg in CATEGORY_SLUG_MAP:
                    target_slugs = CATEGORY_SLUG_MAP[category_arg]
                    products_qs = products_qs.filter(category__slug__in=target_slugs)
                else:
                    products_qs = products_qs.filter(
                        Q(category__slug__iexact=category_arg) |
                        Q(category__name__icontains=category_arg)
                    )

            # Filter by Subcategory in name or description
            if subcategory_arg:
                products_qs = products_qs.filter(
                    Q(name__icontains=subcategory_arg) |
                    Q(description__icontains=subcategory_arg)
                )

            # Filter by Search Text in name or description
            if search_text_arg:
                products_qs = products_qs.filter(
                    Q(name__icontains=search_text_arg) |
                    Q(description__icontains=search_text_arg)
                )

            if rating_applied:
                products_qs = products_qs.order_by("-avg_rating", "-id")
            else:
                products_qs = products_qs.order_by("-id")

        else:
            # Unknown function name fallback
            return JsonResponse({
                "reply": "বুঝতে পারিনি, আবার বলুন।",
                "products": [],
                "action": None
            })

        # Limit to top 12 items for clean display
        products = list(products_qs[:12])
        count = len(products)

        # 5. Build Bengali Voice Reply
        if count == 0:
            reply_text = "এই ধরনের পণ্য পাওয়া যায়নি।"
        else:
            count_bn = to_bn_digits(count)
            if fn_name == "show_offers":
                reply_text = f"{count_bn}টি অফারের পণ্য পাওয়া গেছে।"
            elif condition_applied == "new":
                reply_text = f"{count_bn}টি নতুন পণ্য পাওয়া গেছে।"
            elif condition_applied == "used":
                reply_text = f"{count_bn}টি ব্যবহৃত পণ্য পাওয়া গেছে।"
            elif rating_applied:
                reply_text = f"{count_bn}টি টপ রেটেড পণ্য পাওয়া গেছে।"
            else:
                reply_text = f"{count_bn}টি পণ্য পাওয়া গেছে।"

        # 6. Build Serialized Product Cards for Frontend
        product_cards = []
        for p in products:
            image_url = p.image.url if p.image else ""
            product_url = reverse("product_details", kwargs={"slug": p.slug}) if p.slug else "#"
            condition_text = p.get_condition_display() if hasattr(p, "get_condition_display") else p.condition
            avg_r = round(p.avg_rating, 1) if getattr(p, "avg_rating", None) else None

            product_cards.append({
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "condition": condition_text,
                "avg_rating": avg_r,
                "image_url": image_url,
                "product_url": product_url,
                "category": p.category.name if p.category else "",
                "is_offer": p.is_offer,
            })

        return JsonResponse({
            "reply": reply_text,
            "products": product_cards,
            "action": fn_name,
            "query": user_text
        })

    except Exception as e:
        logger.exception("Error executing database query for voice assistant: %s", e)
        return JsonResponse({
            "reply": "বুঝতে পারিনি, আবার বলুন।",
            "products": [],
            "action": fn_name
        })
