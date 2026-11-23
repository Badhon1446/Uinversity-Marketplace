import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)

# Outdated or deprecated models mapped to current active models for instant response
DEPRECATED_MODEL_ALIASES = {
    "gemini-2.5-flash": "gemini-flash-latest",
    "gemini-2.0-flash": "gemini-flash-latest",
    "gemini-1.5-flash": "gemini-flash-latest",
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

SYSTEM_INSTRUCTION = """
You are the voice search assistant for UniMart, a university student marketplace in Bangladesh.
Students sell their used (second-hand) goods here, and the store also provides brand new products.
Users speak in Bengali (bn-BD), English, or mixed Banglish.

Your job is to identify user intent and call the appropriate function:

1. show_offers():
   - Trigger when user asks for offers, discounts, promotional deals.
   - Examples: "আজকের অফার দেখাও", "অফার কী আছে", "ডিসকাউন্ট পণ্য দেখাও", "today deals", "show offers".

2. show_products(category, subcategory, search_text, condition, min_rating):
   - Trigger when user asks for products, clothes, electronics, gaming, books, food, etc.
   - CONDITION (Crucial for university marketplace):
     * If user asks for "নতুন", "new", "ব্র্যান্ড নিউ", "brand new" -> set condition="new".
     * If user asks for "ব্যবহৃত", "পুরাতন", "used", "সেকেন্ড হ্যান্ড", "second hand", "student used" -> set condition="used".
     * If condition is not mentioned, leave it null.
   - RATING:
     * If user asks for "টপ রেটেড", "ভালো রেটিং", "top rated" -> set min_rating=4.
     * If user asks for specific stars (e.g. "৫ স্টার", "৪ স্টার") -> set min_rating to that number.
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
        "description": "Search and show products by category, subcategory, condition (new/used), rating, and search text.",
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
                    "description": "Product subcategory or item type in English (e.g. shirt, pant, t-shirt, sharee, ps5, laptop, tv, ssd, mouse, keyboard, watch).",
                },
                "condition": {
                    "type": "STRING",
                    "description": "Condition of the product: 'new' (brand new) or 'used' (student used / second-hand).",
                    "enum": ["new", "used"],
                },
                "min_rating": {
                    "type": "INTEGER",
                    "description": "Minimum product rating between 1 and 5 (e.g. 4 for top rated).",
                },
                "search_text": {
                    "type": "STRING",
                    "description": "Optional search keyword or product name in English.",
                },
            },
        },
    },
]


def _resolve_model_name(raw_name: str) -> str:
    """Resolve and map deprecated model names directly to active ones without 404 delay."""
    name = (raw_name or "").strip()
    return DEPRECATED_MODEL_ALIASES.get(name, name) if name else "gemini-flash-latest"


def _call_gemini_via_sdk(user_text: str, api_key: str, model_name: str):
    """Attempt calling Gemini via official google-genai SDK."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

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
        description="Search and show products by category, subcategory, condition, rating, and optional search text.",
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
                    description="Minimum rating 1-5.",
                ),
                "search_text": types.Schema(
                    type=types.Type.STRING,
                    description="Optional search text in English.",
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
            "error": None
        }

    return {"function_name": None, "args": {}, "error": None}


def _call_gemini_via_rest(user_text: str, api_key: str, model_name: str):
    """Direct fast REST API call for Gemini Function Calling."""
    import requests

    candidate_models = [model_name]
    fallback_models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.5-flash"]
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
            resp = requests.post(url, json=payload, timeout=8)
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
                                "error": None
                            }
                return {"function_name": None, "args": {}, "error": None}

            elif resp.status_code == 404:
                logger.warning("Gemini model %s returned 404, attempting fallback...", model)
                last_error = f"Model {model} returned 404"
                continue
            else:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                logger.error("Gemini API error (%s): %s", resp.status_code, err_msg)
                last_error = f"HTTP_{resp.status_code}: {err_msg}"
                if resp.status_code in (400, 403):
                    break

        except Exception as e:
            logger.exception("Error connecting to Gemini REST API: %s", e)
            last_error = str(e)

    return {"function_name": None, "args": {}, "error": last_error}


def analyze_user_voice_query(user_text: str):
    """
    Analyzes user speech with Gemini API using Function Calling.
    Prioritizes official google-genai SDK and gracefully uses fast REST API with automatic model mapping.
    """
    if not user_text or not user_text.strip():
        return {"function_name": None, "args": {}, "error": "Empty input"}

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    raw_model = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest")
    model_name = _resolve_model_name(raw_model)

    if not api_key:
        logger.warning("GEMINI_API_KEY is not configured in settings or environment.")
        return {
            "function_name": None,
            "args": {},
            "error": "API_KEY_NOT_CONFIGURED"
        }

    # 1. Try official google-genai SDK if available
    try:
        import google.genai  # noqa
        return _call_gemini_via_sdk(user_text, api_key, model_name)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("google-genai SDK error (%s), switching to fast REST client.", e)

    # 2. Fast REST API
    return _call_gemini_via_rest(user_text, api_key, model_name)
