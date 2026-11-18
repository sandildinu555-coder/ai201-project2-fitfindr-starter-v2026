import json
import os
import re
import time
from datetime import datetime, timezone

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable

LOG_FILE = os.path.join("logs", "runs.jsonl")


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


def _recover_powershell_dollars(query: str) -> str:
    r"""
    When a user runs `python app.py ask "... $30 ..."` using double quotes in
    Windows PowerShell, PowerShell strips `$30` as an unset variable before
    passing arguments to Python. This function inspects the last line of
    PowerShell's PSReadLine history and restores the stripped `$number` token
    if and only if removing `$\d+` from the raw argument matches `query`.
    """
    if not query or "$" in query:
        return query
    try:
        appdata = os.environ.get("APPDATA", "")
        hist_path = os.path.join(
            appdata,
            "Microsoft",
            "Windows",
            "PowerShell",
            "PSReadLine",
            "ConsoleHost_history.txt",
        )
        if not os.path.exists(hist_path):
            return query
        with open(hist_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return query
        last_cmd = lines[-1]
        candidates = re.findall(r'"([^"]+)"', last_cmd) + re.findall(r"'([^']+)'", last_cmd)
        norm_query = re.sub(r"\s+", " ", query).strip()
        for candidate in candidates:
            if "$" in candidate:
                stripped = re.sub(r"\$\d+(?:\.\d+)?", "", candidate)
                if re.sub(r"\s+", " ", stripped).strip() == norm_query:
                    return candidate
    except Exception:  # noqa: BLE001
        pass
    return query


def _log_run(session: dict, duration_ms: float, model_calls: int) -> None:
    """
    Write one structured JSONL record per run to logs/runs.jsonl.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    parsed = session.get("parsed") or {}

    if session.get("missing_fields"):
        status = "blocked_missing_params"
    elif session.get("error"):
        status = "stopped_no_match_or_error"
    else:
        status = "success"

    est_tokens = model_calls * 350
    est_cost_usd = round(model_calls * 0.00007, 6)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": session.get("query"),
        "status": status,
        "categories": parsed.get("categories", []),
        "size": parsed.get("size"),
        "min_price": parsed.get("min_price"),
        "max_price": parsed.get("max_price"),
        "brands": parsed.get("brands", ["any"]),
        "matches_found": len(session.get("search_results") or []),
        "selected_item": (session.get("selected_item") or {}).get("title"),
        "model_calls": model_calls,
        "estimated_tokens": est_tokens,
        "estimated_cost_usd": est_cost_usd,
        "duration_ms": round(duration_ms, 2),
        "output_or_error": session.get("fit_card") or session.get("error"),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── parsing & validating the query ────────────────────────────────────────────

_SIZE_WORDS = r"XXS|XS|S|M|L|XL|XXL"

# Supports "$20 to $45", "between $20 and $45", "between 20 and 45", "$20-$45"
_PRICE_RANGE_RE = re.compile(
    r"(?:between\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:-|to|and)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:\$|dollars?|usd|bucks?)?|\$\s*(\d+(?:\.\d+)?)\s*(?:-|to|and)\s*\$?\s*(\d+(?:\.\d+)?))",
    re.I,
)
# Supports "under $30", "under 30", "$30", "30$", "30 dollars", "30 bucks"
_PRICE_RE = re.compile(
    r"(?:(?:under|below|less than|max|up to)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:\$|dollars?|usd|bucks?)?|\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\$|dollars?|usd|bucks?))\b",
    re.I,
)

_SIZE_RE = re.compile(rf"\bsize\s+({_SIZE_WORDS}|US\s*\d+(?:\.\d+)?|W\d+)\b", re.I)
_BARE_SIZE_RE = re.compile(rf",\s*({_SIZE_WORDS})\s*$", re.I)

_ANY_BRAND_RE = re.compile(r"\b(?:any\s+brand|no\s+brand)\b", re.I)
_KNOWN_BRANDS = [
    "levi's", "levis", "levi", "louis vuitton", "adidas", "nike", "carhartt",
    "gucci", "zara", "uniqlo", "patagonia", "converse", "dr. martens",
    "doc martens", "champion", "wrangler", "gap", "reformation",
    "brandy melville", "dickies", "vans", "new balance", "coach", "ralph lauren",
]

_STOP_WORDS = {
    "i", "want", "need", "looking", "for", "find", "me", "get", "a", "an", "the",
    "some", "outfit", "outfits", "clothes", "clothing", "good", "looking", "nice",
    "and", "or", "both", "in", "on", "with", "from", "by", "brand", "brands",
    "under", "below", "between", "to", "max", "size", "dollars", "dollar", "usd", "bucks",
}


def _extract_brands(text: str) -> tuple[list[str], str]:
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
    tokens = re.findall(r"[a-zA-Z0-9]+", description.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def parse_query(query: str) -> dict:
    text = _recover_powershell_dollars(query or "")

    min_price = None
    max_price = None
    range_match = _PRICE_RANGE_RE.search(text)
    if range_match:
        g1, g2, g3, g4 = range_match.groups()
        min_price = float(g1 if g1 is not None else g3)
        max_price = float(g2 if g2 is not None else g4)
        text = text[: range_match.start()] + " " + text[range_match.end() :]
    else:
        price_match = _PRICE_RE.search(text)
        if price_match:
            val = next(g for g in price_match.groups() if g is not None)
            max_price = float(val)
            text = text[: price_match.start()] + " " + text[price_match.end() :]

    size = None
    size_match = _SIZE_RE.search(text) or _BARE_SIZE_RE.search(text)
    if size_match:
        size = re.sub(r"\s+", " ", size_match.group(1)).strip().upper()
        text = text[: size_match.start()] + " " + text[size_match.end() :]

    brands, text = _extract_brands(text)

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
    results = _call_search(parsed["description"], parsed["size"], parsed["max_price"])

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

    min_price = parsed.get("min_price")
    if min_price is not None:
        results = [item for item in results if (item.get("price") or 0) >= min_price]

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
    recovered_query = _recover_powershell_dollars(query)
    session = new_session(recovered_query, wardrobe)
    steps = 0
    model_calls = 0
    start_time = time.perf_counter()

    try:
        steps += 1
        trace.check_iterations(steps)
        parsed = parse_query(recovered_query)
        session["parsed"] = parsed
        trace.step("parse_query", inputs=recovered_query, returned=parsed)

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
            _log_run(session, (time.perf_counter() - start_time) * 1000, model_calls)
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
            _log_run(session, (time.perf_counter() - start_time) * 1000, model_calls)
            return session

        steps += 1
        trace.check_iterations(steps)
        session["selected_item"] = results[0]
        trace.step("select_item", returned=session["selected_item"])

        steps += 1
        trace.check_iterations(steps)
        model_calls += 1
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
        model_calls += 1
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

    _log_run(session, (time.perf_counter() - start_time) * 1000, model_calls)
    return session


def _nothing_found_message(parsed: dict) -> str:
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
        query="Levi's vintage jeans size W28 between $20 and $45",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== 3. Incomplete multi-category query (Gatekeeper blocks & asks for size/price) ===")
    _show(run_agent(
        query="I want a classical summer and spring beach outfit",
        wardrobe=get_example_wardrobe(),
    ))