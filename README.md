# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## Stretch Features (declared before building)

I'm attempting all three stretch features. Declared here first; the sections
further down describe what each one changed once built.

1. **A fourth tool — `compare_price(item)`.** Compares the selected listing's
   price with the median price of other listings in the same category and
   returns a verdict (`good deal` / `fair` / `above typical` / `no comparison`).
2. **A second branch — swap an overpriced pick.** If `compare_price` says the
   top result is `above typical` and another search result in the same category
   is cheaper, the loop selects the cheaper one instead (and records why) before
   calling `suggest_outfit`.
3. **Style memory — `--memory`.** With `python app.py ask '...' --memory`, the
   wardrobe is loaded from `memory/wardrobe.json` instead of the example
   wardrobe, and each successful find is saved into it, so the next run's
   outfits can use pieces found in earlier runs. `--forget` clears it.

---

## What This Does

You type what you're hunting for in plain language — e.g. `'vintage graphic tee
under $30, size M'`. FitFindr pulls a price ceiling and size out of the query,
searches 40 thrift listings (Depop, thredUp, Poshmark), and picks the best
keyword match. It then suggests two outfits pairing that item with pieces from
your wardrobe, and writes a 2–4 sentence caption you could actually post. If
nothing matches, it stops before calling the model and tells you which
constraint to loosen.

---

## Tool Inventory

All three live in `tools.py`.

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size, then ranks what's left by keyword overlap with the description (title hit = 2 points, hit in description/category/style_tags/colors/brand = 1).
- **Inputs:** `description` (str), `size` (str or None), `max_price` (float or None, inclusive).
  Size is a **token** match, not a substring: `"M"` matches `M`, `S/M`, `M/L`; `"L"` matches `L/XL` but not `XL`; shoe/waist sizes (`US 9`, `W30`) only match whole; `One Size` items match any letter size.
- **Returns:** `list[dict]` of listing dicts, best score first (ties → cheaper first), at most `config.SEARCH_RESULT_LIMIT` (10). Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
- **When it has nothing:** `[]` — an empty list, never `None` and never an exception. Also `[]` if the description has no usable keywords.

### `suggest_outfit`

- **What it does:** Asks the model for two outfits built around the new item, naming pieces from the user's wardrobe.
- **Inputs:** `new_item` (dict — one listing dict from `search_listings`), `wardrobe` (dict with an `items` key holding a list of wardrobe-item dicts: `name`, `category`, `colors`, `style_tags`, `notes`).
- **Returns:** `str` — non-empty outfit text, under ~90 words, naming owned pieces exactly as written in the wardrobe.
- **When it has nothing:** If `wardrobe["items"]` is empty, it returns general styling advice using common basics instead of failing. If the model returns an empty string, it returns a one-line fallback (`"Style the <title> with simple basics in neutral colors."`). It never returns `""`.

### `create_fit_card`

- **What it does:** Asks the model for a social-media caption in the voice of someone who just bought the item.
- **Inputs:** `outfit` (str — output of `suggest_outfit`), `new_item` (dict — the same listing dict).
- **Returns:** `str` — a 2–4 sentence caption mentioning the item, price and platform once each, with at most two emoji and two hashtags. Brand is only included in the prompt when it isn't `None`.
- **When it has nothing:** If `outfit` is empty or whitespace, returns `"Couldn't write a fit card for <title>: no outfit suggestion was provided."` without calling the model.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` naming what was searched and what to loosen (drop the size,
raise the price limit, use broader words), and return the session without
calling `suggest_outfit`. Otherwise, take the first result as
`session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent` (message built by `agent.py::_no_results_message`)

**How the query is parsed:** Regex, in `agent.py::parse_query`. A price comes
from `under/below/less than/max $N` or a bare `$N`; a size from `size X` (letter
sizes, `US 9`, `W30 L30`). Both are cut out of the text and what remains
(minus filler like "looking for") is the description.

**What moves through the session:** `query` → `parsed` → `search_results` →
`selected_item` → `outfit_suggestion` → `fit_card` (or `error`). Each loop
iteration reads the session to decide the next step — the first `None` field
determines which tool runs — and `trace.check_iterations` caps the loop at
`config.MAX_ITERATIONS`.

---

## Sample Run

**One full query** (plus the empty-search path, to show the branch)

```
$ python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1**
- Y2K Baby Tee — Butterfly Print
- Baggy straight-leg jeans, dark wash
- Vintage black denim jacket
- Chunky white sneakers
- Black crossbody bag

**Outfit 2**
- Y2K Baby Tee — Butterfly Print
- Wide-leg khaki trousers
- Black cropped zip hoodie
- Black combat boots
- Brown leather belt

  Fit card: Scored this little butterfly tee on Depop for just $18 and I’m so obsessed with the pink and purple Y2K print. It’s giving total 2000s mall rat energy, especially paired with baggy denim or wide-leg trousers. 🦋✨ #y2kstyle #depopfind

2 model calls this session, 468 prompt + 150 output tokens
```

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown', size XXS, under $5. Try to drop the size, or raise the price limit, or use broader words (e.g. 'dress' instead of 'designer ballgown').

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_024', 'title': 'Vintage Polo Shirt — Forest Green', 'description': 'Classic polo in forest green. Short sleeve, ribbed collar. Slightly boxy. The kind of piece that goes with everything.', 'category': 'tops', 'style_tags': ['vintage', 'preppy', 'classic', 'earth tones'], 'size': 'M', 'condition': 'good', 'price': 18.0, 'colors': ['green', 'forest green'], 'brand': 'Ralph Lauren', 'platform': 'thredUp'}, {'id': 'lst_003', 'title': 'Oversized Flannel Shirt — Plaid Red/Black', 'description': 'Classic oversized flannel. Great layering piece. A few tiny pulls in the fabric but nothing visible when worn.', 'category': 'tops', 'style_tags': ['grunge', 'vintage', 'flannel', 'streetwear', 'layering'], 'size': 'XL (oversized)', 'condition': 'good', 'price': 22.0, 'colors': ['red', 'black'], 'brand': 'Woolrich', 'platform': 'thredUp'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

```
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', 'XXS', 5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
**Outfit 1**
Pair the vintage Levi's 501 jeans with the white ribbed tank top, black cropped zip hoodie, and chunky white sneakers. Add the black crossbody bag for a casual, effortless streetwear look.

**Outfit 2**
Style the vintage Levi's 501 jeans with the oversized grey crewneck sweatshirt, black combat boots, and the brown leather belt. Layer the vintage black denim jacket on top for a classic, edgy vintage aesthetic.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501s on Depop for just $38 and I am never taking them off. The medium wash has that perfectly broken-in indigo fade that's impossible to fake. Can't wait to wear these with crisp white sneakers for that ultimate effortless streetwear look. 👖✨ #thrifted #levis
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('', load_listings()[0]))"
Couldn't write a fit card for Vintage Levi's 501 Jeans — Medium Wash: no outfit suggestion was provided.
```

---

## How I Used AI

<!-- TODO(you): check these match your experience and reword in your own voice. -->

**Moment 1**

- *What I asked for:* I had Claude Code implement `search_listings` from the spec in the starter docstring, which warns that `"s" in "us 9"` is True.
- *What came back:* A size filter that splits sizes into tokens (`S/M` → `S`, `M`) and compares shoe/waist sizes whole, so `M` matches `S/M` but `S` doesn't match `US 9` and `L` doesn't match `XL`.
- *What I changed:* I checked it against every size in the data (`L/XL`, `One Size (adjustable)`, `W30 L30`, …) and kept the rule that one-size items match any letter size, then wrote that rule into the Tool Inventory.

**Moment 2**

- *What I asked for:* A `create_fit_card` prompt that sounds like a real post and mentions price and platform once.
- *What came back:* The first full run produced *"It's up on my Depop right now for just $19. Grab it before I change my mind"* — a seller's caption, not a buyer's.
- *What I changed:* I changed the prompt to say the caption is from someone who just **bought** the find and is not selling it. The next run read *"Scored this little butterfly tee on Depop for just $18…"*.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
