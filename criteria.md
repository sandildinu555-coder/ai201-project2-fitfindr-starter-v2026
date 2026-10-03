## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
I chose 4 of 5 because my search relies on basic regex and keyword matching. If a user phrases their query in a highly unusual way, the parser might miss the parameters, causing the search to fail even if a matching item exists in the database.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
5 of 5 is the target because conditional branching logic should be 100% deterministic. If the search list is completely empty, the `if not results:` rule should trigger perfectly every single time without exception.

---

## 3. The item state is preserved between tools

The item dictionary stored in `session["selected_item"]` is identical to the `new_item` dictionary passed into the `suggest_outfit` tool, in 5 of 5 tries.

**Why this target:**
If the state isn't preserved correctly, the agent might suggest an outfit for a completely different item than the one the user just found, making the app useless. 5 of 5 is required because data passing between functions should never fail.

---

## 4. The fit card is concise and specific

The generated fit card caption explicitly includes the `brand` or `title` of the new item and is under 40 words, in at least 4 of 5 tries.

**Why this target:**
I chose 4 of 5 because Large Language Models can occasionally be unpredictable with exact word counts, but a strong prompt should enforce brevity and mention the specific item the vast majority of the time.

---

## 5. The empty wardrobe gracefully degrades

If a query matches an item but the user's wardrobe is completely empty, the `suggest_outfit` tool returns general styling advice without crashing, in 5 of 5 tries.

**Why this target:**
New users won't have saved any items yet, so the application must handle this empty state gracefully and still provide value rather than breaking. 5 of 5 is the target because handling an empty dictionary is basic programmatic error handling.