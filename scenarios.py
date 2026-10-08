"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    # Criterion 3 names 5 specific queries (app.py's EXAMPLE_QUERIES[:-1]) and
    # checks, for each one, that the item search_listings found is the item
    # that reached the fit card. Criterion 5 names its own 5 queries, checking
    # price/size compliance instead — 4 of its 5 queries are the same strings
    # as criterion 3's. Rather than duplicate scenarios for overlapping
    # queries, each distinct query gets ONE scenario here; criteria 1, 3, 4,
    # and 5 are all scored off whichever scenarios their own query list names
    # (criterion 1's scenario above already covers 'vintage graphic tee under
    # $30' for criteria 3, 4, and 5 too).
    {
        # Criterion 3 (also feeds criterion 5 — same query is in both lists).
        "name": "session passing: track jacket",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 3 (also feeds criterion 5).
        "name": "session passing: slip dress",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 3 only — criterion 5 asks for 'sneakers size US 9' instead.
        "name": "session passing: sneakers size 8",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 3 (also feeds criterion 5). Example wardrobe, unlike the
        # "empty wardrobe" diagnostic scenario above which uses this same
        # query with no wardrobe items — different test, kept separate.
        "name": "session passing: denim jacket",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 5 only — the one query in its list not already covered.
        "name": "price/size check: sneakers US 9",
        "query": "sneakers size US 9",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
