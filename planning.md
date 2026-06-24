# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings(description, size, max_price)

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the mock secondhand listings dataset and returns items that match the user’s request.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A short natural-language description of the item the user wants, such as "vintage graphic tee" or "black leather jacket". This should be compared against listing fields like title, description, category, style_tags, and colors.
- `size` (str | None): The requested size, such as "M", "L", "W30 L30", or None if the user did not provide a size. If size is None, the tool should not filter by size.
- `max_price` (float | None): The highest price the user is willing to pay. For example, if the user says “under $30,” this value should be 30.0. If the user does not provide a price limit, this can be None.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of matching listing dictionaries, sorted by relevance.

Each item in the list is one listing from `listings.json`, with fields such as `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

If matches are found, the return value looks like:

[
    {
        "id": str,
        "title": str,
        "description": str,
        "category": str,
        "style_tags": list[str],
        "size": str,
        "condition": str,
        "price": float,
        "colors": list[str],
        "brand": str | None,
        "platform": str
    }
]

Each field represents a para meter in the listing.json.
**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
Return the following
[]
---

### Tool 2: suggest_outfit(new_item, wardrobe)

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool returns a string with outfit suggestions, using specific wardrobe pieces when available or general styling advice when the wardrobe is empty.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The listing selected from search_listings. It should include fields such as title, category, style_tags, colors, price, condition, brand, and platform.
- `wardrobe` (dict): The user’s wardrobe data. It should contain an "items" key with a list of wardrobe item dictionaries. Each wardrobe item should include fields such as name, category, colors, and style_tags.

**What it returns:**
<!-- Describe the return value -->
A non-empty string with outfit suggestions.

If the wardrobe has usable items, the string should suggest specific outfit combinations using the selected listing and named pieces from the wardrobe.

If the wardrobe is empty, the tool should still return general styling advice instead of crashing or returning an empty string.
**What happens if it fails or returns nothing:**
If `new_item` is missing or empty, the tool should return a clear error string:

"Cannot suggest an outfit because no item was provided."

If the wardrobe is empty, this is not treated as a hard failure. The tool should return general styling advice for the selected item, and the agent can still continue to `create_fit_card`.

If the tool returns an empty string for any reason, the agent should stop before calling `create_fit_card`, store the issue in session state, and explain that it could not create a styling suggestion.
---

### Tool 3: create_fit_card(outfit, new_item)

**What it does:**
<!-- Describe what this tool does in 1-2 sentences -->
Creates a short, shareable caption based on the selected listing and the styling suggestion.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The styling suggestion string returned by `suggest_outfit`. This may include specific wardrobe pieces or general styling advice.

-  `new_item` (dict):   The selected listing from search_listings. This is the item the user might buy. It is passed separately because the required tool signature is create_fit_card(outfit, new_item), and it gives the caption direct access to listing details like title, price, platform, condition, colors, and style_tags

**What it returns:**
<!-- Describe the return value -->
A non-empty string with a short fit card caption.

The caption should use the selected item, its price/platform, and the styling suggestion. It should sound like a casual social media caption, not a product description.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If `outfit` is missing, empty, or only whitespace, the tool should return a clear error string:

"Cannot create a fit card because the outfit suggestion is missing."

If `new_item` is missing or empty, the tool should return a clear error string:

"Cannot create a fit card because no selected item was provided."

If the tool returns an empty string for any reason, the agent should not present it as a normal fit card. The agent should store the issue in session state and explain that the caption could not be generated.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent first reads the user query and extracts the search inputs: description, size, and max_price. It then calls search_listings(description, size, max_price). Since search_listings returns a list, the agent checks whether the list is empty. If the list is empty, the agent stops early and tells the user that no matching listing was found.

If the list has results, the agent stores the first result as selected_item and calls suggest_outfit(selected_item, wardrobe). Since suggest_outfit returns a string, the agent checks whether the string is usable and non-empty. If it is empty or looks like an error message, the agent stops and explains that it found an item but could not create a useful styling suggestion. If the styling suggestion works, the agent stores it as outfit and calls create_fit_card(outfit, selected_item). The agent is done when it has a selected item, a styling suggestion string, and a fit card string to return to the user.
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent uses a session dictionary to keep track of information during one interaction. The session stores the original user query, extracted search inputs, search results, selected item, wardrobe, outfit suggestion, fit card, and any error message.

The output from each tool is stored in the session before the next tool runs. For example, search_listings returns a list of matching listings, and the agent stores the first listing as selected_item. That selected_item is passed into suggest_outfit along with the wardrobe. The string returned from suggest_outfit is stored as outfit, and both outfit and selected_item are passed into create_fit_card.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the requested description, size, and price | The tool returns an empty list `[]`. The agent sees that there are no results, saves the issue in `session["error"]`, stops before calling `suggest_outfit`, and tells the user that nothing matched their search. |
| `suggest_outfit` | No item was provided / `new_item` is missing | The tool returns a clear error string instead of crashing. The agent saves the issue in `session["error"]`, stops before calling `create_fit_card`, and explains that it cannot style anything until a listing has been selected. |
| `suggest_outfit` | Wardrobe is empty | This is not a hard failure. The tool gives general styling advice for the selected item instead of using named wardrobe pieces, and the agent can still move on to `create_fit_card`. |
| `suggest_outfit` | The tool returns an empty string | The agent saves the issue in `session["error"]`, stops before calling `create_fit_card`, and explains that it could not create a useful styling suggestion. |
| `create_fit_card` | Outfit suggestion is missing, empty, or incomplete | The tool returns a clear error string instead of crashing. The agent saves the issue in `session["error"]` and explains that the fit card could not be generated. |
| `create_fit_card` | Selected item is missing | The tool returns a clear error string. The agent does not treat it as a real caption and explains that the fit card needs the selected listing details, like title, price, and platform. |
| `create_fit_card` | Fit card output is empty or unusable | The agent does not show a blank caption. It saves the issue in `session["error"]` and tells the user that the final fit card could not be created properly. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

User query
    |
    | description, size, max_price, wardrobe context
    v
Planning Loop
    |
    +--> search_listings(description, size, max_price)
    |        |
    |        +--> if results == []
    |        |        |
    |        |        v
    |        |    [ERROR] "No listings found..." -> return
    |        |
    |        +--> if results == [item, ...]
    |                 |
    |                 v
    |             Session:
    |             search_results = results
    |             selected_item = results[0]
    |
    +--> suggest_outfit(selected_item, wardrobe)
    |        |
    |        +--> if outfit == "" or outfit is an error string
    |        |        |
    |        |        v
    |        |    [ERROR] "Could not create styling suggestion..." -> return
    |        |
    |        +--> if outfit is a usable string
    |                 |
    |                 v
    |             Session:
    |             outfit = "styling suggestion string"
    |
    +--> create_fit_card(outfit, selected_item)
             |
             +--> if fit_card == "" or fit_card is an error string
             |        |
             |        v
             |    [ERROR] "Could not create fit card..." -> return
             |
             +--> if fit_card is a usable string
                      |
                      v
                  Session:
                  fit_card = "caption string"
                      |
                      v
                  Return final response to user
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader - then test it against 3 queries
     before trusting it" is a plan. -->

### Milestone 1: Search tool

I will use ChatGPT to help build `search_listings`. I will give it the Tool 1 section from `planning.md`, the listings data structure, and the note that it should use `load_listings()` from `utils/data_loader.py`.

I expect it to produce a function that returns a list of matching listing dictionaries, sorted by relevance. Before using it, I will check that it filters by description, size, and max price, and that it returns an empty list `[]` when nothing matches.

### Milestone 2: Outfit suggestion tool

I will use ChatGPT to help build `suggest_outfit`. I will give it the Tool 2 section from `planning.md`, the wardrobe schema, and the note that this tool should return a string, not a dictionary.

I expect it to produce a function that returns a non-empty styling suggestion string using the selected item and the wardrobe. Before using it, I will check that it handles an empty wardrobe by giving general styling advice instead of crashing.

### Milestone 3: Fit card tool

I will use ChatGPT to help build `create_fit_card`. I will give it the Tool 3 section from `planning.md` and explain that its `outfit` input is the styling suggestion string returned by `suggest_outfit`.

I expect it to produce a short caption-style string using the selected item, price, platform, and styling suggestion. Before using it, I will check that it returns a clear error string if the outfit or selected item is missing.

### Milestone 4: Planning loop

I will use ChatGPT to help connect the tools. I will give it the Planning Loop section and the Architecture diagram from `planning.md`.

I expect it to produce logic that stores state, calls `search_listings` first, stops if the returned list is empty, calls `suggest_outfit` only after a selected item exists, and calls `create_fit_card` only after the outfit suggestion string is usable.








---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish - tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent first reads the user's request and identifies the search inputs: the user wants a vintage graphic tee, the max price is 30.0, and no exact size was mentioned, so size is None. It calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)` to search the mock listings dataset.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
`search_listings` returns a list of matching listing dictionaries, sorted by relevance. For example, the first result might be "Faded Band Tee", priced at $22, in good condition on Depop. The agent stores this first result as `selected_item` in the session state, so later tools can use it without asking the user to repeat the item information.

**Step 3:**
<!-- Continue until the full interaction is complete -->
The agent then uses the selected item and the wardrobe context from the user's query, such as baggy jeans and chunky sneakers. It calls `suggest_outfit(new_item=selected_item, wardrobe=wardrobe)`. This tool returns a styling suggestion string, such as pairing the faded band tee with baggy jeans and chunky sneakers for a relaxed 90s-inspired look. The agent stores this string as `outfit`, then calls `create_fit_card(outfit=outfit, new_item=selected_item)`. This tool returns a short caption-style fit card based on the selected listing and the styling suggestion.

**Final output to user:**
<!-- What does the user actually see at the end? -->
I found a good option: the Faded Band Tee for $22 on Depop in good condition. I'd style it with your baggy jeans and chunky sneakers for a relaxed 90s look - casual, easy, and still put together.

Fit card: "found this faded band tee for $22 and it's going straight into the baggy jeans + chunky sneakers rotation low effort, good fit."

**Error path:**
If `search_listings` returns an empty list, the agent should not continue to `suggest_outfit` or `create_fit_card`. Instead, it should tell the user that nothing matched the current constraints and suggest trying a broader description, higher budget, or fewer constraints.