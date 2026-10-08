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

import config
from generate import generate
from utils.data_loader import load_listings


# Words that carry no meaning for matching ("a tee for me" → "tee").
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to",
    "me", "my", "i", "im", "looking", "want", "need", "some", "something",
    "find", "get", "under", "below", "less", "than", "size", "please", "any",
}

# A few spellings the listings use differently from how people type them.
_SYNONYMS = {
    "tee": {"tee", "t-shirt", "tshirt", "shirt"},
    "tshirt": {"tee", "t-shirt", "tshirt", "shirt"},
    "sneakers": {"sneakers", "sneaker", "shoes", "trainers"},
    "jeans": {"jeans", "denim"},
    "hoodie": {"hoodie", "sweatshirt"},
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9'\-]+", text.lower())


def _size_tokens(size: str) -> set[str]:
    """'S/M' → {'S', 'M'};  'XL (oversized)' → {'XL', 'OVERSIZED'};  'US 9' → {'US 9'}."""
    s = size.upper().strip()
    if s.startswith("US ") or s.startswith("W"):
        # Shoe and waist sizes are compared whole, never split into letters.
        return {s}
    return {t for t in re.split(r"[/\s()]+", s) if t}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Token match, not substring: 'M' matches 'M', 'S/M', 'M/L' but not 'US 9';
    'L' matches 'L/XL' but not 'XL'. One-size items match any letter size.
    """
    wanted_u = wanted.upper().strip()
    listing_u = listing_size.upper().strip()
    if wanted_u == listing_u:
        return True
    if listing_u.startswith("ONE SIZE") and not wanted_u.startswith(("US ", "W")):
        return True
    return wanted_u in _size_tokens(listing_size)


def _score(listing: dict, keywords: list[str]) -> int:
    """Keyword overlap. A title hit counts double — titles are what sellers lead with."""
    title = set(_words(listing["title"]))
    body = set(_words(" ".join([
        listing["description"],
        listing["category"],
        " ".join(listing["style_tags"]),
        " ".join(listing["colors"]),
        listing.get("brand") or "",
    ])))
    score = 0
    for kw in keywords:
        variants = _SYNONYMS.get(kw, {kw})
        if variants & title:
            score += 2
        elif variants & body:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = [w for w in _words(description) if w not in _STOPWORDS and len(w) > 1]
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    # Highest score first; cheaper wins a tie.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_line = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_line}\n\n"
            "They haven't told us anything about their wardrobe. Suggest two "
            "outfits built around this item using common basics most people own "
            "(e.g. plain jeans, a white tee, sneakers). Name each piece. "
            "Keep it under 90 words, no preamble."
        )
    else:
        owned = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w.get('colors', []))})"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_line}\n\n"
            f"Here is what they already own:\n{owned}\n\n"
            "Suggest two outfits that pair the new item with pieces from that "
            "list. Name the owned pieces exactly as written. Keep it under 90 "
            "words, no preamble."
        )

    response = generate(prompt).strip()
    # The contract is a non-empty string; never hand the loop "".
    return response or f"Style the {new_item['title']} with simple basics in neutral colors."


def _describe_item(item: dict) -> str:
    """One line about a listing. Brand is often None, so it's only added when present."""
    parts = [item["title"], f"${item['price']:.2f}", f"size {item['size']}",
             f"{item['condition']} condition", f"on {item['platform']}"]
    if item.get("brand"):
        parts.insert(1, f"brand {item['brand']}")
    colors = ", ".join(item.get("colors", []))
    tags = ", ".join(item.get("style_tags", []))
    return " · ".join(parts) + f"\nColors: {colors}. Style: {tags}."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            f"Couldn't write a fit card for {new_item.get('title', 'this item')}: "
            "no outfit suggestion was provided."
        )

    prompt = (
        f"Write an Instagram/TikTok caption from someone who just BOUGHT this thrift find (they are not selling it).\n\n"
        f"Item: {_describe_item(new_item)}\n"
        f"How it'll be styled: {outfit}\n\n"
        "Rules: 2 to 4 sentences. Sound like a real person posting, not a "
        "product listing. Mention the item, the price as a dollar figure "
        "(e.g. $19, never spelled out like \"nineteen bucks\") and the "
        "platform once each. Be specific about the vibe. At most two emoji "
        "and two hashtags. "
        "Open with something other than a variant of \"Scored this\" or "
        "\"Just scored\" — don't lead with the verb \"scored\" at all. Start "
        "the first sentence a different way each time: a reaction, a "
        "question, a scene-setting detail, whatever fits, but not the same "
        "sentence shape you'd default to. "
        "Return only the caption."
    )
    response = generate(prompt).strip()
    return response or f"Thrifted the {new_item['title']} for ${new_item['price']:.2f} on {new_item['platform']}."


# ── Tool 4 (stretch): compare_price ───────────────────────────────────────────

def compare_price(item: dict) -> dict:
    """
    Compare a listing's price with other listings in the same category.

    Args:
        item: a listing dict.

    Returns:
        {"item_price": float, "typical_price": float | None,
         "n_compared": int, "verdict": str}
        verdict is "good deal" (≤ 80% of the category median), "above typical"
        (≥ 125% of it), or "fair" in between.

        When there's nothing to compare against (no other listing in the
        category), typical_price is None, n_compared is 0 and the verdict is
        "no comparison". It never raises.
    """
    others = [
        l["price"] for l in load_listings()
        if l["category"] == item.get("category") and l["id"] != item.get("id")
    ]
    result = {"item_price": item["price"], "typical_price": None,
              "n_compared": len(others), "verdict": "no comparison"}
    if not others:
        return result

    others.sort()
    mid = len(others) // 2
    median = others[mid] if len(others) % 2 else (others[mid - 1] + others[mid]) / 2
    result["typical_price"] = median

    ratio = item["price"] / median
    if ratio <= 0.8:
        result["verdict"] = "good deal"
    elif ratio >= 1.25:
        result["verdict"] = "above typical"
    else:
        result["verdict"] = "fair"
    return result
