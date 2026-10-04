"""
Style memory (stretch): a wardrobe that persists between runs.

Each successful find is saved as a wardrobe item, so the next run's
suggest_outfit can pair the new item with things found earlier.

    python app.py ask 'vintage graphic tee under $30' --memory
    python app.py ask 'baggy jeans' --memory      ← outfits now use the tee
    python app.py ask --forget                    ← clear it
"""

import json

import config

MEMORY_FILE = config.ROOT / "memory" / "wardrobe.json"


def load_wardrobe() -> dict:
    """The saved wardrobe, or an empty one ({"items": []}) if nothing is saved."""
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        return {"items": list(data.get("items", []))}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": []}


def remember(item: dict) -> bool:
    """Add a found listing to the saved wardrobe. False if it was already there."""
    wardrobe = load_wardrobe()
    if any(w.get("id") == item["id"] for w in wardrobe["items"]):
        return False
    wardrobe["items"].append({
        "id": item["id"],
        "name": item["title"],
        "category": item["category"],
        "colors": item.get("colors", []),
        "style_tags": item.get("style_tags", []),
        "notes": f"Found on {item['platform']} for ${item['price']:.2f}",
    })
    MEMORY_FILE.parent.mkdir(exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(wardrobe, indent=2), encoding="utf-8")
    return True


def forget() -> None:
    MEMORY_FILE.unlink(missing_ok=True)
