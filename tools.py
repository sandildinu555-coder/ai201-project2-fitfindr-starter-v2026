"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re
import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

# ── Helper Functions for search_listings ──────────────────────────────────────

_STOPWORDS = {"a", "an", "the", "for", "in", "on", "with", "under", "and", "or", "to", "of", "is"}

def _keywords(text: str) -> set[str]:
    """Extracts lowercase words, ignoring standard stopwords."""
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in _STOPWORDS}

def _size_tokens(size_str: str) -> set[str]:
    """Extracts alphanumeric tokens from a size string."""
    if not size_str:
        return set()
    return set(re.findall(r'\b[a-z0-9]+\b', size_str.lower()))

def _size_matches(query_size: str, item_size: str) -> bool:
    """Checks if sizes match, allowing 'one size' to match anything."""
    if "one size" in item_size.lower():
        return True
    q_tokens = _size_tokens(query_size)
    i_tokens = _size_tokens(item_size)
    return bool(q_tokens & i_tokens)

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.
    """
    # 1. Load every listing
    listings = load_listings()
    
    # Extract keywords from the user's description
    query_kws = _keywords(description)
    
    scored_listings = []
    
    for item in listings:
        # 2. Filter by max_price (if provided)
        if max_price is not None:
            if item.get("price", 0.0) > max_price:
                continue
                
        # 2. Filter by size (if provided)
        if size is not None:
            item_size = item.get("size", "")
            if not item_size or not _size_matches(size, item_size):
                continue
                
        # 3. Score by keyword overlap (search title, description, and tags)
        text_to_search = f"{item.get('title', '')} {item.get('description', '')} {' '.join(item.get('style_tags', []))}"
        item_kws = _keywords(text_to_search)
        
        score = len(query_kws & item_kws)
        
        # 4. Drop anything scoring zero
        if score > 0:
            scored_listings.append((score, item))
            
    # 5. Sort by score, highest first
    scored_listings.sort(key=lambda x: x[0], reverse=True)
    
    # Extract just the dictionaries and limit the results
    limit = getattr(config, 'SEARCH_RESULT_LIMIT', 5)
    return [item for score, item in scored_listings[:limit]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.
    """
    # 1. Check whether wardrobe['items'] is empty
    wardrobe_items = wardrobe.get('items', [])
    
    item_title = new_item.get('title', 'this item')
    item_desc = new_item.get('description', '')
    new_item_details = f"{item_title} - {item_desc}"

    if not wardrobe_items:
        # 2. If wardrobe is empty, ask for general styling ideas
        prompt = (
            f"The user is considering buying this item: {new_item_details}.\n"
            "Their wardrobe information is currently empty. "
            "Please suggest some general, trendy styling ideas and what kind of outfits they could build around this item. "
            "Keep it short, friendly, and practical (2-3 sentences)."
        )
    else:
        # 3. If not empty, format the wardrobe items into the prompt
        owned_clothes = ""
        for w_item in wardrobe_items:
            colors = ", ".join(w_item.get('colors', []))
            owned_clothes += f"- {w_item.get('name', 'Clothing item')} ({colors})\n"
            
        prompt = (
            f"The user is considering buying this item: {new_item_details}.\n"
            f"They already own the following items in their wardrobe:\n{owned_clothes}\n"
            "Suggest 1 or 2 specific outfits combining the new item ONLY with the pieces they already own. "
            "Keep the tone helpful and stylish, around 2-3 sentences."
        )

    # 4. Return the model's response
    return generate(prompt)

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.
    """
    # 1. Guard against an empty or whitespace-only outfit
    if not outfit or not outfit.strip():
        return "Just snagged a cool new piece! Can't wait to figure out how to style it. 💫"

    
    title = new_item.get('title', 'this item')
    price = new_item.get('price', 'a great price')
    platform = new_item.get('platform', 'a thrift store')

    # 2. Build a prompt with the item details and the outfit
    prompt = (
        f"Write a short, engaging social media caption (2-4 sentences) about finding this item: {title}. "
        f"I just bought it on {platform} for ${price}. "
        f"Here is how I plan to style it: {outfit}\n\n"
        "The caption should read like a real post from a fashion enthusiast sharing their thrifting find. "
        "It MUST mention the item, its price, and the platform exactly once. "
        "Make it sound natural and capture the specific vibe of the outfit. Do not make it sound like a generic product description."
    )

    # 3. Call generate() and return the response
    return generate(prompt)
