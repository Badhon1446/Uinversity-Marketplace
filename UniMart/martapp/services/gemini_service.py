import logging
import json
import re
from django.conf import settings

logger = logging.getLogger(__name__)

# Outdated or deprecated models mapped to current active models for instant response
DEPRECATED_MODEL_ALIASES = {
    "gemini-2.5-flash": "gemini-3.8-flash",
    "gemini-2.0-flash": "gemini-3.8-flash",
    "gemini-1.5-flash": "gemini-3.8-flash",
    "gemini-flash-latest": "gemini-3.8-flash",
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",
}

# Allowed category enum values based on UniMart database
VALID_CATEGORIES = [
    "clothing",
    "electronic_item",
    "gaming",
    "men_collections",
    "food",
    "grocery",
    "toys",
]

BN_TO_EN_DIGITS = {
    "১": "1", "২": "2", "৩": "3", "৪": "4", "৫": "5",
    "1": "1", "2": "2", "3": "3", "4": "4", "5": "5"
}

CATEGORY_KEYWORDS = {
    "clothing": [
        "জামা", "পোশাক", "কাপড়", "কাপড়", "শার্ট", "টি-শার্ট", "টি শার্ট", "টিশার্ট",
        "প্যান্ট", "শাড়ি", "শাড়ি", "shirt", "t-shirt", "tshirt", "pant", "sharee", "sari", "cloth", "dress"
    ],
    "electronic_item": [
        "ল্যাপটপ", "কম্পিউটার", "পিসি", "টিভি", "এসএসডি", "মাউস", "কিবোর্ড", "মনিটর", "ফোন", "আইফোন", "স্মার্টফোন",
        "laptop", "computer", "pc", "tv", "ssd", "mouse", "keyboard", "monitor", "phone", "iphone", "mobile"
    ],
    "gaming": [
        "গেমিং", "gaming", "ps5", "প্লেস্টেশন", "playstation", "xbox", "game"
    ],
    "food": [
        "খাবার", "নুডলস", "food", "noodles", "snack", "বিরিয়ানি", "বিরিয়ানি"
    ],
    "toys": [
        "খেলনা", "গাড়ি", "toy", "toys", "doll", "গান", "water gun"
    ],
    "men_collections": [
        "ঘড়ি", "ঘড়ি", "watch", "বেল্ট", "belt", "মানিব্যাগ", "wallet"
    ]
}

SUBCATEGORY_KEYWORDS = {
    "laptop": ["ল্যাপটপ", "laptop"],
    "tv": ["টিভি", "tv"],
    "ssd": ["এসএসডি", "ssd"],
    "mouse": ["মাউস", "mouse"],
    "keyboard": ["কিবোর্ড", "keyboard"],
    "shirt": ["শার্ট", "shirt"],
    "t-shirt": ["টি-শার্ট", "টি শার্ট", "টিশার্ট", "t-shirt", "tshirt"],
    "pant": ["প্যান্ট", "pant"],
    "sharee": ["শাড়ি", "শাড়ি", "sharee", "sari"],
    "watch": ["ঘড়ি", "ঘড়ি", "watch"],
    "noodles": ["নুডলস", "noodles"],
    "ps5": ["ps5", "প্লেস্টেশন", "playstation"],
    "iphone": ["iphone", "আইফোন"]
}

SYSTEM_INSTRUCTION = """
You are the voice search assistant for UniMart, a university student marketplace in Bangladesh.
Students sell their used (second-hand) goods here, and the store also provides brand new products.
Users speak in Bengali (bn-BD), English, or mixed Banglish.

Your job is to identify user intent and call the appropriate function:

1. show_offers():
   - Trigger when user asks for offers, discounts, promotional deals.
   - Examples: "আজকের অফার দেখাও", "অফার কী আছে", "ডিসকাউন্ট পণ্য দেখাও", "today deals", "show offers".

2. show_products(category, subcategory, search_text, condition, min_rating):
   - Trigger when user asks for products, clothes, electronics, gaming, books, food, specific ratings, etc.
   - RATING & STARS (CRUCIAL):
     * If user mentions specific rating / stars (e.g. "3 star", "3star", "৩ স্টার", "৩স্টার", "3 star rating", "৩ স্টার রেটিং", "3 রেটিং", "৩ রেটিং") -> set min_rating=3.
     * "1 star", "১ স্টার" -> set min_rating=1.
     * "2 star", "২ স্টার" -> set min_rating=2.
     * "4 star", "৪ স্টার" -> set min_rating=4.
     * "5 star", "৫ স্টার" -> set min_rating=5.
     * If user asks for "টপ রেটেড", "ভালো রেটিং", "top rated", "high rating" -> set min_rating=4.
     * If rating is not mentioned, leave min_rating null.
   - CONDITION (Crucial for university marketplace):
     * If user asks for "নতুন", "new", "ব্র্যান্ড নিউ", "brand new" -> set condition="new".
     * If user asks for "ব্যবহৃত", "পুরাতন", "used", "সেকেন্ড হ্যান্ড", "second hand", "student used" -> set condition="used".
     * If condition is not mentioned, leave it null.
   - CATEGORY & SUBCATEGORY (Translate Bengali terms to English):
     * "জামা", "পোশাক", "কাপড়", "শার্ট", "টি-শার্ট", "প্যান্ট", "শাড়ি" -> category: "clothing", subcategory: "shirt"/"t-shirt"/"pant"/"sharee"
     * "গেমিং", "গেমিং আইটেম", "প্লেস্টেশন", "ps5" -> category: "gaming", subcategory: "ps5"
     * "ল্যাপটপ", "কম্পিউটার", "টিভি", "এসএসডি", "মাউস", "কিবোর্ড" -> category: "electronic_item", subcategory: "laptop"/"tv"/"ssd"/"mouse"/"keyboard"
     * "খাবার", "নুডলস" -> category: "food", subcategory: "noodles"
     * "খেলনা", "গাড়ি" -> category: "toys"
     * "ঘড়ি" -> category: "men_collections", subcategory: "watch"
   - Category MUST strictly be one of: ["clothing", "electronic_item", "gaming", "men_collections", "food", "grocery", "toys"].
   - search_text: English keyword or brand name if specifically mentioned (e.g. "Samsung", "HP", "iPhone", "Honda").

If the query is greeting or unrelated to shopping, do NOT call any function.
"""

FUNCTION_DECLARATIONS_DICT = [
    {
        "name": "show_offers",
        "description": "Show all products currently on promotional offer or discount.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "show_products",
        "description": "Search and show products by category, subcategory, condition (new/used), minimum star rating, and search text.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Product category in English.",
                    "enum": VALID_CATEGORIES,
                },
                "subcategory": {
                    "type": "STRING",
                    "description": "Product subcategory or item type in English (e.g. shirt, pant, t-shirt, sharee, ps5, laptop, tv, ssd, mouse, keyboard, watch, iphone).",
                },
                "condition": {
                    "type": "STRING",
                    "description": "Condition of the product: 'new' (brand new) or 'used' (student used / second-hand).",
                    "enum": ["new", "used"],
                },
                "min_rating": {
                    "type": "INTEGER",
                    "description": "Minimum product rating between 1 and 5 (e.g. 3 for 3-star rating, 4 for top rated/4-star, 5 for 5-star).",
                },
                "search_text": {
                    "type": "STRING",
                    "description": "Optional search keyword or product brand name in English.",
                },
            },
        },
    },
]


def _resolve_model_name(raw_name: str) -> str:
    """Resolve and map deprecated model names directly to active ones without 404 delay."""
    name = (raw_name or "").strip()
    return DEPRECATED_MODEL_ALIASES.get(name, name) if name else "gemini-3.8-flash"


def parse_rating_from_text(text: str):
    """
    Extracts numerical star rating (1-5) from Bengali, English or Banglish text.
    Handles '3 star', '3star', '৩ স্টার', '৩স্টার', '3 star rating', '৩ স্টার রেটিং', 'top rated', etc.
    """
    if not text:
        return None

    text_lower = text.lower()
    # Match patterns like: 3 star, 3star, ৩ স্টার, ৩স্টার, 3 rating, ৩ রেটিং
    match = re.search(r"([1-5]|[১-৫])\s*(?:star|স্টার|রেটিং|rating)", text_lower)
    if match:
        digit = match.group(1)
        return int(BN_TO_EN_DIGITS.get(digit, digit))

    # Reverse patterns like: star 3, rating 3, রেটিং ৩
    match_rev = re.search(r"(?:star|স্টার|রেটিং|rating)\s*([1-5]|[১-৫])", text_lower)
    if match_rev:
        digit = match_rev.group(1)
        return int(BN_TO_EN_DIGITS.get(digit, digit))

    # Top rated keywords
    if any(w in text_lower for w in ["টপ রেটেড", "ভালো রেটিং", "টপ রেটিং", "top rated", "high rating"]):
        return 4

    return None


def extract_intent_locally(user_text: str):
    """
    High-speed, zero-downtime local parser fallback.
    Extracts function name and arguments directly from user query when Gemini API is busy (503) or offline.
    """
    if not user_text or not user_text.strip():
        return {"function_name": None, "args": {}, "error": "Empty input"}

    text_lower = user_text.lower().strip()

    # 1. Offers detection
    if any(w in text_lower for w in ["অফার", "ডিসকাউন্ট", "offer", "discount", "deal", "deals"]):
        return {
            "function_name": "show_offers",
            "args": {},
            "source": "local_fallback",
            "error": None
        }

    # 2. Rating extraction
    min_rating = parse_rating_from_text(text_lower)

    # 3. Condition extraction
    condition = None
    if any(w in text_lower for w in ["নতুন", "new", "ব্র্যান্ড নিউ", "brand new"]):
        condition = "new"
    elif any(w in text_lower for w in ["ব্যবহৃত", "পুরাতন", "used", "সেকেন্ড হ্যান্ড", "সেকেন্ডহ্যান্ড", "second hand"]):
        condition = "used"

    # 4. Category and Subcategory extraction
    category = None
    subcategory = None

    for sub_k, words in SUBCATEGORY_KEYWORDS.items():
        if any(w in text_lower for w in words):
            subcategory = sub_k
            break

    for cat_k, words in CATEGORY_KEYWORDS.items():
        if any(w in text_lower for w in words):
            category = cat_k
            break

    # If subcategory was found without category, map default category
    if subcategory and not category:
        if subcategory in ["shirt", "t-shirt", "pant", "sharee"]:
            category = "clothing"
        elif subcategory in ["laptop", "tv", "ssd", "mouse", "keyboard", "iphone"]:
            category = "electronic_item"
        elif subcategory == "watch":
            category = "men_collections"
        elif subcategory == "ps5":
            category = "gaming"
        elif subcategory == "noodles":
            category = "food"

    # 5. Search text extraction (brand names)
    search_text = None
    brands = ["samsung", "hp", "dell", "asus", "lenovo", "apple", "iphone", "honda", "civic", "sony", "nike"]
    for b in brands:
        if b in text_lower:
            search_text = b
            break

    # General product intent keywords
    product_intent = any(w in text_lower for w in [
        "পণ্য", "প্রোডাক্ট", "জিনিস", "আইটেম", "product", "item", "কি কি আছে", "দেখাও", "show", "search", "খুঁজে"
    ])

    if min_rating or condition or category or subcategory or search_text or product_intent:
        args = {}
        if category:
            args["category"] = category
        if subcategory:
            args["subcategory"] = subcategory
        if condition:
            args["condition"] = condition
        if min_rating:
            args["min_rating"] = min_rating
        if search_text:
            args["search_text"] = search_text

        return {
            "function_name": "show_products",
            "args": args,
            "source": "local_fallback",
            "error": None
        }

    return {"function_name": None, "args": {}, "error": None}


def _call_gemini_via_sdk(user_text: str, api_key: str, model_name: str):
    """Attempt calling Gemini via official google-genai SDK using v1beta endpoint."""
    from google import genai
    from google.genai import types

    # Explicitly use v1beta to ensure support for modern models and function calling
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

    show_offers_decl = types.FunctionDeclaration(
        name="show_offers",
        description="Show all products currently on promotional offer or discount.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={},
        ),
    )

    show_products_decl = types.FunctionDeclaration(
        name="show_products",
        description="Search and show products by category, subcategory, condition, minimum star rating, and optional search text.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "category": types.Schema(
                    type=types.Type.STRING,
                    description="Product category in English.",
                    enum=VALID_CATEGORIES,
                ),
                "subcategory": types.Schema(
                    type=types.Type.STRING,
                    description="Product subcategory or item type in English.",
                ),
                "condition": types.Schema(
                    type=types.Type.STRING,
                    description="Condition of the product: 'new' or 'used'.",
                    enum=["new", "used"],
                ),
                "min_rating": types.Schema(
                    type=types.Type.INTEGER,
                    description="Minimum product star rating between 1 and 5 (e.g. 3 for 3-star rating).",
                ),
                "search_text": types.Schema(
                    type=types.Type.STRING,
                    description="Optional search text or brand in English.",
                ),
            },
        ),
    )

    tools = [types.Tool(function_declarations=[show_offers_decl, show_products_decl])]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=tools,
        temperature=0.0,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=user_text.strip(),
        config=config,
    )

    if response and response.function_calls:
        first_call = response.function_calls[0]
        fn_name = getattr(first_call, "name", None)
        fn_args = getattr(first_call, "args", {}) or {}

        if hasattr(fn_args, "items"):
            fn_args = dict(fn_args)
        elif not isinstance(fn_args, dict):
            fn_args = {}

        return {
            "function_name": fn_name,
            "args": fn_args,
            "source": "gemini_sdk",
            "error": None
        }

    return {"function_name": None, "args": {}, "error": None}


def _call_gemini_via_rest(user_text: str, api_key: str, model_name: str):
    """Direct fast REST API call for Gemini Function Calling with automatic candidate fallbacks."""
    import requests

    candidate_models = [model_name]
    fallback_models = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]
    for m in fallback_models:
        if m not in candidate_models:
            candidate_models.append(m)

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_text.strip()}]
            }
        ],
        "tools": [
            {
                "function_declarations": FUNCTION_DECLARATIONS_DICT
            }
        ],
        "generationConfig": {
            "temperature": 0.0
        }
    }

    last_error = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "functionCall" in part:
                            fn_call = part["functionCall"]
                            return {
                                "function_name": fn_call.get("name"),
                                "args": fn_call.get("args") or {},
                                "source": f"gemini_rest_{model}",
                                "error": None
                            }
                return {"function_name": None, "args": {}, "error": None}

            elif resp.status_code == 404:
                logger.warning("Gemini model %s returned 404, attempting fallback...", model)
                last_error = f"Model {model} returned 404"
                continue
            elif resp.status_code == 503:
                logger.warning("Gemini model %s experienced 503 high demand, attempting fallback...", model)
                last_error = f"Model {model} returned 503"
                continue
            else:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                logger.error("Gemini API error (%s): %s", resp.status_code, err_msg)
                last_error = f"HTTP_{resp.status_code}: {err_msg}"
                if resp.status_code in (400, 403):
                    break

        except Exception as e:
            logger.warning("Error connecting to Gemini REST API for %s: %s", model, e)
            last_error = str(e)

    return {"function_name": None, "args": {}, "error": last_error}


def analyze_user_voice_query(user_text: str):
    """
    Analyzes user speech with Gemini API using Function Calling.
    If Gemini API encounters 503 spikes, network timeouts, or errors, seamlessly fails over
    to the high-speed local intent parser to guarantee 100% availability and zero failure.
    """
    if not user_text or not user_text.strip():
        return {"function_name": None, "args": {}, "error": "Empty input"}

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    raw_model = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
    model_name = _resolve_model_name(raw_model)

    # 1. Try official google-genai SDK if API key is provided
    if api_key:
        try:
            import google.genai  # noqa
            sdk_result = _call_gemini_via_sdk(user_text, api_key, model_name)
            if sdk_result.get("function_name"):
                return sdk_result
        except ImportError:
            pass
        except Exception as e:
            logger.warning("google-genai SDK error (%s), switching to fast REST client.", e)

        # 2. Try fast REST API
        rest_result = _call_gemini_via_rest(user_text, api_key, model_name)
        if rest_result.get("function_name"):
            return rest_result

    # 3. Zero-Downtime Smart Local Fallback
    # If Gemini API is 503 / timing out / key missing, extract intent locally with regex + rules!
    local_result = extract_intent_locally(user_text)
    if local_result.get("function_name"):
        logger.info("Gemini unavailable or returned no function. Successfully resolved query via local parser.")
        return local_result

    return {
        "function_name": None,
        "args": {},
        "error": "Could not determine intent"
    }
