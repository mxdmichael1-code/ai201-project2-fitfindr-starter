"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
import json
from urllib import error, request

from dotenv import load_dotenv

from utils.data_loader import load_listings

load_dotenv()

DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_DOUBAO_MODEL = "doubao-1-5-pro-32k-250115"


# ── LLM client ────────────────────────────────────────────────────────────────

def _get_llm_config() -> tuple[str, str, str]:
    """Return Doubao-compatible API settings from environment variables."""
    api_key = (
        os.environ.get("DOUBAO_API_KEY")
        or os.environ.get("ARK_API_KEY")
        or os.environ.get("GROQ_API_KEY")
    )
    if api_key:
        api_key = api_key.strip().strip("'\"")
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:].strip()
    if not api_key:
        raise ValueError(
            "No LLM API key set. Add DOUBAO_API_KEY, ARK_API_KEY, or GROQ_API_KEY to .env."
        )
    base_url = os.environ.get("DOUBAO_BASE_URL", DOUBAO_BASE_URL).rstrip("/")
    model = (
        os.environ.get("DOUBAO_MODEL")
        or os.environ.get("ARK_MODEL")
        or os.environ.get("GROQ_MODEL")
        or DEFAULT_DOUBAO_MODEL
    )
    return api_key, base_url, model

def _call_groq(prompt: str, temperature: float = 0.7) -> str:
    """
    Small helper for calling the LLM and returning the model's text response.
    If something goes wrong, return a clear error string instead of crashing.
    """
    try:
        api_key, base_url, model = _get_llm_config()
    except Exception as e:
        return f"LLM call failed: {e}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a practical secondhand fashion assistant. "
                    "Give concise, useful styling advice. Avoid sounding like a product ad."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 300,
    }

    chat_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(chat_request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except error.HTTPError as e:
        detail = e.read().decode("utf-8")
        if e.code == 401 and "API key format is incorrect" in detail:
            detail += (
                " Check that .env contains the Ark/Doubao API key value itself, "
                "not a model name, endpoint id, app id, or console URL."
            )
        return f"LLM call failed: Error code: {e.code} - {detail}"
    except Exception as e:
        return f"LLM call failed: {e}"
# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    if not description or not description.strip():
        return []

    try:
        listings = load_listings()
    except Exception:
        return []

    query_tokens = set(
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9']+", description)
        if len(token) > 1
    )

    if not query_tokens:
        return []

    scored_results = []

    for listing in listings:
        # Price filter
        if max_price is not None:
            try:
                if float(listing.get("price", 0)) > max_price:
                    continue
            except (TypeError, ValueError):
                continue

        # Size filter
        if size is not None:
            requested_size = str(size).lower().strip()
            listing_size = str(listing.get("size", "")).lower().strip()

            # Example: "M" should match "S/M"
            if requested_size not in listing_size:
                continue

        # Build searchable text from listing fields
        searchable_parts = [
            str(listing.get("title", "")),
            str(listing.get("description", "")),
            str(listing.get("category", "")),
            " ".join(listing.get("style_tags", [])),
            " ".join(listing.get("colors", [])),
            str(listing.get("brand", "")),
            str(listing.get("platform", "")),
        ]

        searchable_text = " ".join(searchable_parts).lower()
        listing_tokens = set(re.findall(r"[a-zA-Z0-9']+", searchable_text))

        # Basic relevance score by keyword overlap
        score = len(query_tokens.intersection(listing_tokens))

        # Small bonus if the exact phrase appears
        if description.lower().strip() in searchable_text:
            score += 3

        if score > 0:
            scored_results.append((score, listing))

    scored_results.sort(
        key=lambda pair: (
            pair[0],
            -float(pair[1].get("price", 0)),
        ),
        reverse=True,
    )

    return [listing for score, listing in scored_results]
    # Replace this with your implementation
    return []


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not new_item:
        return "Cannot suggest an outfit because no item was provided."

    item_title = new_item.get("title", "this item")
    item_category = new_item.get("category", "unknown category")
    item_colors = ", ".join(new_item.get("colors", [])) or "unknown colors"
    item_tags = ", ".join(new_item.get("style_tags", [])) or "no style tags"
    item_description = new_item.get("description", "")

    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []

    if not wardrobe_items:
        prompt = f"""
The user is considering buying this secondhand item:

Title: {item_title}
Category: {item_category}
Colors: {item_colors}
Style tags: {item_tags}
Description: {item_description}

The user has not provided any usable wardrobe items yet.

Suggest 1-2 practical ways to style this item using general clothing categories.
Keep it concise, specific, and casual.
Do not say you cannot help just because the wardrobe is empty.
"""
        return _call_groq(prompt, temperature=0.6)

    wardrobe_text = "\n".join(
        [
            f"- {item.get('name', 'Unnamed item')} "
            f"({item.get('category', 'unknown category')}; "
            f"colors: {', '.join(item.get('colors', [])) or 'unknown'}; "
            f"style tags: {', '.join(item.get('style_tags', [])) or 'none'})"
            for item in wardrobe_items
        ]
    )

    prompt = f"""
The user is considering buying this secondhand item:

Title: {item_title}
Category: {item_category}
Colors: {item_colors}
Style tags: {item_tags}
Description: {item_description}

The user's wardrobe includes:
{wardrobe_text}

Suggest 1-2 complete outfits using the new item and named pieces from the wardrobe when they fit.
Explain briefly why the pieces work together.
Keep the response concise and natural.
"""
    return _call_groq(prompt, temperature=0.7)
    return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    
    if not outfit or not outfit.strip():
        return "Cannot create a fit card because the outfit suggestion is missing."

    if not new_item:
        return "Cannot create a fit card because no selected item was provided."

    item_title = new_item.get("title", "this thrifted find")
    item_price = new_item.get("price", "unknown price")
    item_platform = new_item.get("platform", "the platform")
    item_condition = new_item.get("condition", "unknown condition")
    item_colors = ", ".join(new_item.get("colors", [])) or "unknown colors"
    item_tags = ", ".join(new_item.get("style_tags", [])) or "no style tags"

    prompt = f"""
Create a short social-media-style fit card caption.

Selected item:
- Title: {item_title}
- Price: ${item_price}
- Platform: {item_platform}
- Condition: {item_condition}
- Colors: {item_colors}
- Style tags: {item_tags}

Styling suggestion:
{outfit}

Requirements:
- 2 to 4 sentences
- Sounds casual and authentic, like a real OOTD caption
- Mention the item name, price, and platform naturally once
- Capture the outfit vibe
- Do not sound like a product description
"""
    return _call_groq(prompt, temperature=0.9)
    return ""


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    results = search_listings(
        description="vintage graphic tee",
        size=None,
        max_price=30.0,
    )

    print(f"Found {len(results)} results.")

    if results:
        selected_item = results[0]
        print("Selected:", selected_item["title"])

        wardrobe = get_example_wardrobe()

        outfit = suggest_outfit(selected_item, wardrobe)
        print("\nOutfit suggestion:")
        print(outfit)

        fit_card = create_fit_card(outfit, selected_item)
        print("\nFit card:")
        print(fit_card)
    else:
        print("No matching listings found.")
