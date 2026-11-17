import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # extracted parameters (description, categories, size, min/max_price, brands)
        "missing_fields": [],        # mandatory fields missing from the query (Capstone gatekeeper)
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── parsing & validating the query ────────────────────────────────────────────

_SIZE_WORDS = r"XXS|XS|S|M|L|XL|XXL|SMALL|MEDIUM|LARGE"
_SIZE_MAP = {"SMALL": "S", "MEDIUM": "M", "LARGE": "L"}

# Price range (e.g., "$20 to $40", "$20-$40", "between $20 and $40")
_PRICE_RANGE_RE = re.compile(
    r"(?:between\s*)?\$\s*(\d+(?:\.\d+)?)\s*(?:-|to|and)\s*\$?\s*(\d+(?:\.\d+)?)",
    re.I,
)
# Single max price (e.g., "under $30", "max $40", "$30")
_PRICE_RE = re.compile(r"(?:under|below|less than|max|up to)?\s*\$\s*(\d+(?:\.\d+)?)", re.I)

_SIZE_RE = re.compile(rf"\bsize\s+({_SIZE_WORDS}|US\s*\d+(?:\.\d+)?|W\d+)\b", re.I)
_BARE_SIZE_RE = re.compile(rf"(?:,|\b)\s*({_SIZE_WORDS})\b", re.I)

# Known brands + explicit "brand: X" or "any brand" patterns
_ANY_BRAND_RE = re.compile(r"\b(?:any\s+brand|no\s+brand)\b", re.I)
_KNOWN_BRANDS = [
    "levi's", "levis", "levi", "louis vuitton", "adidas", "nike", "carhartt",
    "gucci", "zara", "uniqlo", "patagonia", "converse", "dr. martens",
    "doc martens", "champion", "wrangler", "gap", "reformation",
    "brandy melville", "dickies", "vans", "new balance", "coach", "ralph lauren",
]

# Stop words to strip when splitting a description into multiple style/occasion/item categories
_STOP_WORDS = {
    "i", "want", "need", "looking", "for", "find", "me", "get", "a", "an", "the",
    "some", "outfit", "outfits", "clothes", "clothing", "good", "looking", "nice",
    "and", "or", "both", "in", "on", "with", "from", "by", "brand", "brands",
}


def _extract_brands(text: str) -> tuple[list[str], str]:
    """
    Extract one or more brands from the query.
    If none are mentioned (or user says 'any brand'), default to ['any'] without asking.
    Returns (brands_list, cleaned_text).
    """
    cleaned = text
    if _ANY_BRAND_RE.search(cleaned):
        cleaned = _ANY_BRAND_RE.sub(" ", cleaned)
        return ["any"], cleaned

    found_brands = []
    for brand in _KNOWN_BRANDS:
        pattern = re.compile(rf"\b{re.escape(brand)}\b", re.I)
        if pattern.search(cleaned):
            canonical = "levi's" if brand in ("levi", "levis", "levi's") else brand.lower()
            if canonical not in found_brands:
                found_brands.append(canonical)
            cleaned = pattern.sub(" ", cleaned)

    if not found_brands:
        return ["any"], cleaned

    return found_brands, cleaned


def _extract_categories(description: str) -> list[str]:
    """
    Break a cleaned description into distinct category/style/occasion keywords
    so multi-category queries (e.g. 'classical summer and spring beach tee')
    are tracked cleanly.
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", description.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def parse_query(query: str) -> dict:
    """
    Pull description, categories, size, min/max price, and brands out of the query.
    """
    text = query or ""

    # 1. Price or Price Range
    min_price = None
    max_price = None
    range_match = _PRICE_RANGE_RE.search(text)
    if range_match:
        min_price = float(range_match.group(1))
        max_price = float(range_match.group(2))
        text = text[: range_match.start()] + " " + text[range_match.end() :]
    else:
        price_match = _PRICE_RE.search(text)
        if price_match:
            max_price = float(price_match.group(1))
            text = text[: price_match.start()] + " " + text[price_match.end() :]

    # 2. Size
    size = None
    size_match = _SIZE_RE.search(text) or _BARE_SIZE_RE.search(text)
    if size_match:
        raw_size = re.sub(r"\s+", " ", size_match.group(1)).strip().upper()
        size = _SIZE_MAP.get(raw_size, raw_size)
        text = text[: size_match.start()] + " " + text[size_match.end() :]

    # 3. Brands (defaults to ["any"] if not mentioned)
    brands, text = _extract_brands(text)

    # 4. Description & Multiple Categories
    description = re.sub(r"[,\s]+", " ", text).strip(" ,")
    categories = _extract_categories(description)
    cleaned_description = " ".join(categories) if categories else ""

    return {
        "description": cleaned_description,
        "categories": categories,
        "size": size,
        "min_price": min_price,
        "max_price": max_price,
        "brands": brands,
    }


def validate_query(parsed: dict) -> list[str]:
    """
    Pre-flight gatekeeper: checks mandatory parameters before calling tools:
      1. Clothing type / occasion / style categories (at least 1 required)
      2. Size
      3. Price or price range
    Note: Brand is NEVER asked for if omitted; it automatically defaults to ['any'].
    """
    missing = []

    if not parsed.get("categories"):
        missing.append("clothing type or occasion/style (e.g., 'summer beach shirt', 'spring and summer graphic tee')")

    if not parsed.get("size"):
        missing.append("size (e.g., S, M, L)")

    max_price = parsed.get("max_price")
    if max_price is None or max_price <= 0:
        missing.append("price or price range (e.g., under $40, or $20-$40)")

    return missing


def _clarification_message(missing: list[str], parsed: dict) -> str:
    """
    Build a follow-up question asking only for the missing mandatory parameters.
    """
    cats = parsed.get("categories") or []
    context = f" for {', '.join(cats)!r}" if cats else ""
    brand_info = (
        f" (brand filter: {', '.join(parsed['brands'])})"
        if parsed.get("brands") and parsed["brands"] != ["any"]
        else ""
    )
    return (
        f"Clarification needed{context}{brand_info} before searching listings. "
        f"Please specify your {', and '.join(missing)}."
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def _call_search(desc: str, size: str | None, max_price: float | None) -> list[dict]:
    """
    Call search_listings over MCP with fallback to direct tool call.
    """
    try:
        from mcp_client import call_tool

        results = call_tool(
            "search_listings",
            {"description": desc, "size": size, "max_price": max_price},
        )
        return results or []
    except Exception:  # noqa: BLE001
        return search_listings(desc, size, max_price)


def _search(parsed: dict) -> list[dict]:
    """
    Execute search supporting multiple categories, price ranges, and strict brand filtering.
    """
    results = _call_search(parsed["description"], parsed["size"], parsed["max_price"])

    # If a multi-category query (e.g. "spring and summer tee") didn't match all words at once,
    # search each category keyword individually and merge unique listings.
    categories = parsed.get("categories") or []
    if not results and len(categories) > 1:
        seen_ids = set()
        merged = []
        for cat in categories:
            for item in _call_search(cat, parsed["size"], parsed["max_price"]):
                item_id = item.get("id") or item.get("title")
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    merged.append(item)
        results = merged

    # Filter by minimum price if user provided a price range (e.g. $20-$40)
    min_price = parsed.get("min_price")
    if min_price is not None:
        results = [item for item in results if (item.get("price") or 0) >= min_price]

    # Strict brand filtering if user specified brand(s) other than "any"
    brands = parsed.get("brands") or ["any"]
    if brands != ["any"]:
        filtered_by_brand = []
        for item in results:
            item_brand = (item.get("brand") or "").lower()
            item_title = (item.get("title") or "").lower()
            item_desc = (item.get("description") or "").lower()
            if any(b in item_brand or b in item_title or b in item_desc for b in brands):
                filtered_by_brand.append(item)
        results = filtered_by_brand

    return results


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.
    """
    session = new_session(query, wardrobe)
    steps = 0

    try:
        steps += 1
        trace.check_iterations(steps)
        parsed = parse_query(query)
        session["parsed"] = parsed
        trace.step("parse_query", inputs=query, returned=parsed)

        # ── PRE-FLIGHT GATEKEEPER (CAPSTONE EXTENSION) ────────────────────────
        steps += 1
        trace.check_iterations(steps)
        missing = validate_query(parsed)
        session["missing_fields"] = missing
        if missing:
            session["error"] = _clarification_message(missing, parsed)
            trace.step(
                "validate_query",
                inputs=parsed,
                returned=missing,
                note=f"missing {len(missing)} mandatory field(s): stopping before search_listings",
            )
            return session

        trace.step(
            "validate_query",
            inputs=parsed,
            returned=[],
            note=f"valid (brands={parsed['brands']}, categories={parsed['categories']})",
        )

        steps += 1
        trace.check_iterations(steps)
        results = _search(parsed)
        session["search_results"] = results
        trace.step(
            "search_listings (via MCP)",
            inputs=parsed,
            returned=results,
            note=f"{len(results)} match(es)",
        )

        # ── THE BRANCH ────────────────────────────────────────────────────────
        if not results:
            session["error"] = _nothing_found_message(parsed)
            trace.step(
                "branch",
                note="search returned []: stopping before suggest_outfit",
            )
            return session

        steps += 1
        trace.check_iterations(steps)
        session["selected_item"] = results[0]
        trace.step("select_item", returned=session["selected_item"])

        steps += 1
        trace.check_iterations(steps)
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
        trace.step(
            "suggest_outfit",
            inputs=session["selected_item"],
            returned=session["outfit_suggestion"],
            note=f"{len(session['wardrobe'].get('items') or [])} wardrobe item(s)",
        )

        steps += 1
        trace.check_iterations(steps)
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
        trace.step(
            "create_fit_card",
            inputs=session["selected_item"],
            returned=session["fit_card"],
        )

    except ModelUnavailable as exc:
        session["error"] = (
            f"The model couldn't be reached, so the outfit and caption steps "
            f"didn't run. The search worked — "
            f"{len(session['search_results'])} listing(s) were found. "
            f"Check GEMINI_API_KEY in your .env, then run the same query "
            f"again.\nWhat the service said: {exc}"
        )
        trace.step("model unavailable", note="stopping, search results kept")

    return session


def _nothing_found_message(parsed: dict) -> str:
    """
    What to say when the search comes back empty.
    """
    tried = [f"description {parsed['description']!r}"]
    if parsed.get("brands") and parsed["brands"] != ["any"]:
        tried.append(f"brand(s) {', '.join(parsed['brands'])}")
    if parsed["size"]:
        tried.append(f"size {parsed['size']}")
    if parsed.get("min_price") is not None and parsed.get("max_price") is not None:
        tried.append(f"price range ${parsed['min_price']:g}-${parsed['max_price']:g}")
    elif parsed["max_price"] is not None:
        tried.append(f"under ${parsed['max_price']:g}")

    suggestions = ["try broader words — 'jacket' finds more than 'cropped corduroy jacket'"]
    if parsed.get("brands") and parsed["brands"] != ["any"]:
        suggestions.append("try 'any brand' or another brand")
    if parsed["size"]:
        suggestions.append("drop the size, or try a neighbouring one")
    if parsed["max_price"] is not None:
        suggestions.append(f"raise the price ceiling above ${parsed['max_price']:g}")

    return (
        "Nothing in the listings matched " + ", ".join(tried) + ".\n"
        "Things to change: " + "; ".join(suggestions) + "."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} (brand: {item.get('brand') or 'unbranded'}) — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== 1. Multi-category query (no brand mentioned -> defaults to 'any') ===")
    _show(run_agent(
        query="vintage y2k and graphic tee size M under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== 2. Specific brand + price range query ===")
    _show(run_agent(
        query="Levi's vintage jeans size M between $20 and $45",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== 3. Incomplete multi-category query (Gatekeeper asks for size & price, NOT brand) ===")
    _show(run_agent(
        query="I want a classical summer and spring beach outfit",
        wardrobe=get_example_wardrobe(),
    ))