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

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item state is preserved between tools | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is concise and specific (< 40 words) | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| 5. The empty wardrobe gracefully degrades | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```text
From file: results/run_2026-10-12_2353_before.md (Function: create_fit_card)
[5] create_fit_card
      in:  Platform Sneakers — White Chunky Sole ($48.0, poshmark)
      out: Just scored these Platform Sneakers with the dreamiest white chunky sole on Poshmark for only $48! Obsessed is an understatement...
  try 1: completed — fit card 303 chars
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes | 4 of 5 | MET | All 5 tries successfully reached tool 5 and returned a fit card. |
| 2 | Impossible query stops early | 5 of 5 | MET | All 5 tries correctly triggered the branch rule and stopped before `suggest_outfit`. |
| 3 | State is preserved | 5 of 5 | MET | The item dict from `select_item` perfectly matched the input for `suggest_outfit` 5 times. |
| 4 | Fit card is concise (< 40 words) | 4 of 5 | MISSED | All 5 fit cards generated were over 300 characters (approx. 45-55 words), exceeding the limit. |
| 5 | Empty wardrobe gracefully degrades | 5 of 5 | MET | Handled the empty wardrobe gracefully all 5 times, giving general advice without crashing. |

**Diagnoses**

Criterion 4 missed on 5 out of 5 tries. The failure happened in the `create_fit_card` tool's model output. The mechanism is that the LLM's prompt does not strictly constrain the word count enough. Even though the tool works and correctly grabs the title/brand, the model generates overly descriptive captions that consistently fall around 45-55 words (over 300 characters), thereby breaking the "under 40 words" rule.



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

**What I changed:**
I updated the prompt in the `create_fit_card` tool (inside `tools.py`) to explicitly restrict the length by adding: `"STRICTLY keep the caption under 30 words. Do not exceed this limit under any circumstances."`

**Which failure it was meant to fix:**
This was meant to fix Criterion 4, which was failing because the model generated fit card captions that were too long (consistently over 40 words / 300+ characters).

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item state is preserved between tools | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card is concise and specific (< 40 words) | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. The empty wardrobe gracefully degrades | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:**
Yes, it worked perfectly! By strictly instructing the model to keep the caption under 30 words, the fit card lengths dropped from ~350 characters down to ~130-160 characters (around 20-25 words). Criterion 4 passed 5 out of 5 times.

---

## What's Still Broken

Nothing is broken! Thanks to the prompt improvement, all 5 criteria successfully met their targets. The MCP rewire was also successful and didn't break any existing functionality.



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







## Capstone

**What This Extends**
This project extends FitFindr (Units 3 & 4), an AI styling agent. What is new is a "Pre-flight Parameter Extraction & Validation" layer. Instead of hallucinating missing parameters or running expensive tool pipelines on vague inputs (which wastes API tokens), the agent now features a gatekeeper step. It parses the user's input for mandatory parameters (style/occasion, max price, and size). If any are missing, it explicitly halts the tool execution and asks the user clarifying follow-up questions, saving cost and preventing search failures.

**The Shape**
Shape B — Harden against failure (Input Validation and Cost Optimization). Out of scope for this unit: I am not adding a fourth styling tool to `tools.py`, I am not expanding the underlying clothing database, and I am not building a web UI.