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
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
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

## What This Does

FitFindr is an AI agent that acts as a personal shopping assistant for thrifting. A user asks for a specific clothing item with constraints (like size or price), and the agent searches a simulated store database to find a match. It then looks at the user's current wardrobe to suggest how to style the new item and generates a social media-ready caption for the complete outfit.

---

## Tool Inventory

### `search_listings`

- **What it does:** Searches the simulated store database and filters listings based on the parsed user criteria.
- **Inputs:** `description` (str), `size` (str), `max_price` (float)
- **Returns:** A list of dictionaries representing the matching listings (each containing fields like id, title, price, platform).
- **When it has nothing:** An empty list `[]`.

### `suggest_outfit`

- **What it does:** Takes a matched item and the user's wardrobe, and uses a model to suggest an outfit combination.
- **Inputs:** `new_item` (dict), `wardrobe` (dict)
- **Returns:** A string containing the outfit suggestion and styling advice.
- **When it has nothing:** Returns general fashion advice on how to style the item rather than failing.

### `create_fit_card`

- **What it does:** Generates a short, catchy social media-style caption for the complete outfit.
- **Inputs:** `outfit` (str), `new_item` (dict)
- **Returns:** A string containing the generated caption.
- **When it has nothing:** A fallback error string if the model fails to generate a response.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` naming what the user could change, and return the session without calling `suggest_outfit`. Otherwise, take the first result, put it in `session["selected_item"]`, and continue.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex (Regular Expressions).

**What moves through the session:** `query`, `parsed`, `search_results`, `selected_item`, `wardrobe`, `outfit_suggestion`, `fit_card`, and `error`.
---


## Sample Run
```
$ python agent.py
=== A query the data can match ===
[1] parse_query
      in:  looking for a vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Pair the Y2K butterfly baby tee with your baggy dark-wash straight-leg jeans and chunky white sneakers for an …
      →    10 wardrobe item(s)
[5] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Scored this vintage Y2K butterfly baby tee on Depop for just $18 and I am officially obsessed! 🦋✨ I’m pairing …
  found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
  outfit:   Pair the Y2K butterfly baby tee with your baggy dark-wash straight-leg jeans and chunky white sneakers for an effortless, nostalgic off-duty look. To layer for cooler days, simply throw on your black cropped zip hoodie and accessorize with your black crossbody bag.
  fit card: Scored this vintage Y2K butterfly baby tee on Depop for just $18 and I am officially obsessed! 🦋✨ I’m pairing it with baggy dark-wash denim and chunky sneakers for that ultimate nostalgic off-duty vibe, and throwing on a cropped zip hoodie when it gets chilly. Thrifting wins just hit different!

=== A query it can't ===
[6] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[7] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[8] branch
      →    search returned []: stopping before suggest_outfit
  stopped: Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.
  fit_card is None — it should still be None here
```


**The three tools, tested one at a time**


```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors':['black'], 'brand': None, 'platform': 'depop'}]
```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Pair the vintage Levi's with your white ribbed tank top, brown leather belt, and chunky white sneakers for an effortless, casual-cool daytime look. When the weather cools down, layer your oversized grey crewneck sweatshirt over the tank and swap the sneakers for black combat boots to lean into a grungier aesthetic.
```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored the ultimate everyday uniform with these Vintage Levi's 501 Jeans in the dreamiest medium wash! Found them on Depop for just $38.0, and honestly, nothing beats that broken-in vintage fit. Can't wait to keep it classic and effortless by pairing them with my favorite crisp white sneakers.

---

## How I Used AI

**Moment 1**

- *What I asked for:* I asked the AI why my `search_listings` terminal test was returning an empty list `[]` instead of the expected filtered results after I pasted the new logic.
- *What came back:* The AI explained that the VS Code file wasn't saved yet (indicated by the white dot on the tab), so the terminal was still running the old stub code that simply returned `[]`.
- *What I changed:* I used `Ctrl + S` to save the `tools.py` file and re-ran the terminal command, which successfully returned the dictionary of graphic tees under $30.

**Moment 2**

- *What I asked for:* I asked the AI if I needed to delete all the existing TODO instructions in `agent.py` and replace the entire file with the code snippet my lecturer provided in Slack. 
- *What came back:* The AI confirmed that I should replace the entire file, explaining that the provided code already completed the 8 TODO steps and added a `parse_query` regex function to make the branch logic fully operational.
- *What I changed:* I deleted the original contents of `agent.py` and pasted the completed planning loop logic. This successfully connected all my tools and allowed the agent to handle both matched queries and empty search branches.

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

**Happy path**

```text
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    10 match(es)
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Pair the Y2K butterfly baby tee with your baggy dark-wash straight-leg jeans and chunky white sneakers for an …
      →    10 wardrobe item(s)
[5] create_fit_card
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Scored this vintage Y2K butterfly baby tee on Depop for just $18 and I am officially obsessed! 🦋✨ I’m pairing …

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Pair the Y2K butterfly baby tee with your baggy dark-wash straight-leg jeans and chunky white sneakers for an effortless, nostalgic off-duty look. To layer for cooler days, simply throw on your black cropped zip hoodie and accessorize with your black crossbody bag.

  Fit card: Scored this vintage Y2K butterfly baby tee on Depop for just $18 and I am officially obsessed! 🦋✨ I’m pairing it with baggy dark-wash denim and chunky sneakers for that ultimate nostalgic off-duty vibe, and throwing on a cropped zip hoodie when it gets chilly. Thrifting wins just hit different!
```

**Empty search**

```text
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the listings matched description 'designer ballgown', size XXS, under $5.
Things to change: try broader words — 'jacket' finds more than 'cropped corduroy jacket'; drop the size, or try a neighbouring one; raise the price ceiling above $5.
```

**On the MCP move:** 
I moved the `search_listings` tool to MCP by registering it in `mcp_server.py` and calling it via `mcp_client.call_tool()` in `agent.py`. It successfully returned the same exact filtered list of dictionaries as before, but now runs through the external server protocol.

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
