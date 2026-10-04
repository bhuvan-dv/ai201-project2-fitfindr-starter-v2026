# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
`search_listings` is a plain keyword match after a regex pulls out the price
and size, so some phrasings parse badly (in testing, `"size 8"` wasn't read as
a size at all) and two of the three steps depend on a rate-limited model call
that can fail. One miss in five allows for that; more than one would mean the
parsing or the model call is a real problem, not bad luck.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never calls the model. `run_agent` checks `if not
session["search_results"]` and returns before `suggest_outfit`, and
`search_listings` always returns `[]` (never `None`) on no match. It is fully
deterministic, so anything less than 5 of 5 means the branch is broken.

---

## 3. The item search found is the item the later tools used

For each of the 5 matching queries in `app.py`'s `EXAMPLE_QUERIES`, after
`run_agent` returns, `session["selected_item"]["id"]` is the `id` of an item in
`session["search_results"]`, and the fit card contains that item's exact price
(e.g. `$18`) and its platform name (case-insensitive) — 5 of 5 queries.

**Why this target:**
The item reaches `suggest_outfit` and `create_fit_card` only through
`session["selected_item"]`, never as a value the user retypes, so if the price
and platform of that exact listing show up in the caption, the right item made
it all the way through. Session passing is deterministic code, so I set 5 of 5.
The one risk is the model rounding `$18.00` to `"18 bucks"`, and my prompt
explicitly says to mention the price, so that would count as a miss I want to
see.

---

## 4. The fit card is a postable caption, and it varies

Running `'vintage graphic tee under $30'` 5 times with caching off
(`AI201_CACHE=0`): at least 4 of the 5 fit cards are 2–4 sentences long with at
most 2 hashtags, and all 5 cards have a different first sentence.

**Why this target:**
`create_fit_card` runs at `TEMPERATURE = 0.9` and the prompt asks for 2–4
sentences and at most two hashtags, but the model doesn't always follow
formatting rules exactly, so I allow one card in five to break the length or
hashtag rule. Distinct openings should be 5 of 5 at that temperature; if two
match, the prompt is pushing the model into a template opener like "Scored
this…", which I already saw twice in early runs.

---

## 5. Search respects the price ceiling and the size

For these 5 queries — `'vintage graphic tee under $30'`, `'denim jacket under
$50'`, `'silk slip dress in midi length under $40'`, `'90s track jacket in size
M'`, `'sneakers size US 9'` — every listing in `session["search_results"]` has
`price` ≤ the stated limit, and, when a size is given, a `size` whose `/`- or
space-separated parts include it (so `M` accepts `S/M`, but `S` never accepts
`US 9`) — 5 of 5 queries, with zero violating listings.

**Why this target:**
These filters run in plain Python in `search_listings` before any scoring,
with no model involved, so the result should never vary. The data has messy
sizes (`S/M`, `L/XL`, `US 8.5`, `W30 L30`, `One Size / Oversized`) where a
substring test would let `L` match `XL`, so this criterion exists to catch
exactly that. Even one wrong-size listing means the token-matching rule is
wrong, so the target is all of them.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
