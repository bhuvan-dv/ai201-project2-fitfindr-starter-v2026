"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from mcp_client import call_tool
from tools import suggest_outfit, create_fit_card, compare_price
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "price_check": None,         # what compare_price returned (stretch)
        "swapped_from": None,        # the overpriced pick we replaced, if any (stretch)
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    session["parsed"] = parse_query(query)

    # Each pass looks at what's already in the session and picks the next step.
    steps = 0
    while True:
        steps += 1
        trace.check_iterations(steps)

        if not session["search_results"] and session["selected_item"] is None:
            p = session["parsed"]
            session["search_results"] = call_tool("search_listings", {
                "description": p["description"],
                "size": p["size"],
                "max_price": p["max_price"],
            })
            trace.step(
                "search_listings (via MCP)",
                inputs=f"description={p['description']!r}, size={p['size']!r}, max_price={p['max_price']!r}",
                returned=session["search_results"],
            )

            # THE BRANCH: nothing found → explain what to change and stop.
            if not session["search_results"]:
                session["error"] = _no_results_message(p)
                trace.step("branch: empty search", note="stopping before suggest_outfit")
                return session

            session["selected_item"] = session["search_results"][0]

        elif session["price_check"] is None:
            session["price_check"] = compare_price(session["selected_item"])
            check = session["price_check"]
            trace.step(
                "compare_price",
                inputs=f"item={session['selected_item']['title']!r}",
                returned=f"verdict={check['verdict']!r}, typical_price={check['typical_price']}, n_compared={check['n_compared']}",
            )

            # SECOND BRANCH: the pick is overpriced for its category and a
            # cheaper same-category result exists → switch to that one.
            if session["price_check"]["verdict"] == "above typical":
                alternative = _cheaper_alternative(session)
                if alternative is not None:
                    session["swapped_from"] = session["selected_item"]
                    session["selected_item"] = alternative
                    session["price_check"] = compare_price(alternative)
                    trace.step(
                        "branch: overpriced pick",
                        note=f"swapped to {alternative['title']}",
                    )

        elif session["outfit_suggestion"] is None:
            try:
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"], session["wardrobe"]
                )
            except ModelUnavailable as exc:
                session["error"] = f"Couldn't suggest an outfit — the model couldn't be reached: {exc}"
                trace.step("suggest_outfit", note=f"ModelUnavailable: {exc}")
                return session
            trace.step(
                "suggest_outfit",
                inputs=f"item={session['selected_item']['title']!r}, wardrobe_items={len(session['wardrobe'].get('items') or [])}",
                returned=session["outfit_suggestion"],
            )

        elif session["fit_card"] is None:
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"], session["selected_item"]
                )
            except ModelUnavailable as exc:
                session["error"] = f"Couldn't write a fit card — the model couldn't be reached: {exc}"
                trace.step("create_fit_card", note=f"ModelUnavailable: {exc}")
                return session
            trace.step(
                "create_fit_card",
                inputs=f"outfit_len={len(session['outfit_suggestion'])} chars",
                returned=session["fit_card"],
            )

        else:
            return session


def _cheaper_alternative(session: dict) -> dict | None:
    """Best-ranked search result in the same category that is cheaper and not itself overpriced."""
    current = session["selected_item"]
    for candidate in session["search_results"]:
        if (candidate["id"] != current["id"]
                and candidate["category"] == current["category"]
                and candidate["price"] < current["price"]
                and compare_price(candidate)["verdict"] != "above typical"):
            return candidate
    return None


def parse_query(query: str) -> dict:
    """
    Pull a price ceiling and a size out of the query with regex; whatever is
    left is the description.

        "vintage graphic tee under $30, size M"
          → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
    """
    text = query
    max_price = None
    price = re.search(
        r"(?:under|below|less than|max|<)\s*\$?\s*(\d+(?:\.\d+)?)|\$(\d+(?:\.\d+)?)",
        text, re.IGNORECASE,
    )
    if price:
        max_price = float(price.group(1) or price.group(2))
        text = text[: price.start()] + " " + text[price.end():]

    size = None
    size_match = re.search(
        r"\bsize\s+(us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?|xxs|xs|s|m|l|xl|xxl)\b",
        text, re.IGNORECASE,
    )
    bare = re.search(r"\bsize\s+(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).upper()
    elif bare:
        size_match = bare
        size = f"US {bare.group(1)}"   # a bare number is a shoe size in this data
    if size_match:
        text = text[: size_match.start()] + " " + text[size_match.end():]

    description = re.sub(r"[,.]", " ", text)
    description = re.sub(r"^\s*(i'?m\s+)?(looking for|i want|find me|need)\s+", "", description.strip(), flags=re.IGNORECASE)
    description = " ".join(description.split())
    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what was searched and which constraint to loosen — not just 'No results'."""
    searched = [f"'{parsed['description']}'"]
    tips = []
    if parsed["size"]:
        searched.append(f"size {parsed['size']}")
        tips.append("drop the size")
    if parsed["max_price"] is not None:
        searched.append(f"under ${parsed['max_price']:.0f}")
        tips.append("raise the price limit")
    tips.append("use broader words (e.g. 'dress' instead of 'designer ballgown')")
    return (
        f"No listings matched {', '.join(searched)}. "
        f"Try to {', or '.join(tips)}."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
