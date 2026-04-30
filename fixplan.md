# AI Agent Fix Plan: EPUB Structure & Ordering Validation

## Objective

Ensure the generated EPUB **exactly mirrors the structure, order, and content flow** of
Witch Cult Translations

The EPUB must be a **faithful linearization** of the website reading experience.

---

# Phase 1 — Source-of-Truth Ordering Extraction

## 1.1 Build Canonical Chapter List (CRITICAL)

DO NOT rely on:

* URL patterns
* Chapter numbers in titles
* Scraping order

INSTEAD:

For each Arc:

1. Open Arc page
2. Parse DOM in visual reading order
3. Extract chapter links exactly as displayed

If phases exist:

* Traverse phase sections **top → bottom**
* Inside each phase: extract links **top → bottom**

Store ordered structure like:

```json
Arc {
  phases: [
    {
      name: "Phase 1",
      chapters: [link1, link2, link3]
    }
  ]
}
```

If no phases:

```json
Arc {
  chapters: [link1, link2, link3]
}
```

---

## 1.2 Detect Special Chapters

While parsing, explicitly classify:

* Prologue
* Interlude(s)
* Side Stories (if present)
* Epilogue

Do NOT assume numeric ordering.

Use keyword detection in titles:

| Type      | Keywords    |
| --------- | ----------- |
| Prologue  | "Prologue"  |
| Interlude | "Interlude" |
| Epilogue  | "Epilogue"  |

Store them **in-place** as they appear in the arc page.

---

# Phase 2 — Chapter De-duplication

## 2.1 Canonical URL Deduplication

Before scraping content:

* Normalize URLs (remove trailing slashes, query params)
* Maintain a `visited_urls` set

If URL already processed → SKIP

---

## 2.2 Title-Based Duplicate Detection

Some duplicates differ by URL.

Normalize title:

* lowercase
* strip whitespace
* remove punctuation

If normalized title already exists → FLAG duplicate

---

## 2.3 Navigation Link Filtering

DO NOT collect links from:

* "Previous Chapter"
* "Next Chapter"
* "Recent Posts"
* "Related Posts"

ONLY collect from:

* Arc page
* Phase sections

---

# Phase 3 — Content Integrity Fixes

## 3.1 Correct Missing Prologue

If Prologue missing:

1. Scan arc page again for "Prologue"
2. If found but not scraped → insert at correct index (usually first)

If still missing:

* Attempt recovery via:

  * site search
  * adjacent chapter navigation

---

## 3.2 Fix Interlude Placement

Rule:

Interludes must appear **exactly where listed on arc page**

NOT:

* At the beginning
* Not grouped incorrectly

Agent must NOT reorder based on assumptions.

---

## 3.3 Validate Sequential Flow

After building list:

Check:

* No gaps
* No unexpected jumps
* Logical progression

Example checks:

* Prologue should be before Chapter 1
* Interludes should match site position
* Epilogue should be last (if present)

---

# Phase 4 — EPUB Structure Fix

## 4.1 Preserve HTML Hierarchy

From chapter page:

Extract ONLY main content container:

Common selectors:

* `article`
* `.entry-content`
* `.post-content`

Preserve:

* `<p>`
* `<br>`
* `<em>`, `<strong>`
* `<h1–h3>`

REMOVE:

* navigation elements
* share buttons
* ads
* comments

---

## 4.2 Fix Broken Formatting

Common problems to correct:

* Missing paragraph spacing
* Collapsed line breaks
* Inline text blobs

Solutions:

* Convert `<br>` sequences → paragraph breaks
* Ensure each paragraph wrapped in `<p>`
* Preserve intentional italics/emphasis

---

## 4.3 Chapter File Naming (EPUB)

Use stable ordering index:

```
001_prologue.xhtml
002_chapter_1.xhtml
003_chapter_2.xhtml
...
```

DO NOT rely on titles for ordering.

---

# Phase 5 — Order Verification System (MANDATORY)

## 5.1 Build Verification Pass

After scraping:

1. Re-fetch arc page
2. Reconstruct expected order
3. Compare with scraped list

Check:

* Same chapter count
* Same sequence
* Same titles (fuzzy match allowed)

---

## 5.2 Detect Errors

Flag if:

* Missing chapters
* Extra chapters
* Duplicate chapters
* Misordered entries

---

## 5.3 Auto-Correction Strategy

If mismatch detected:

* Rebuild chapter list from source
* Re-map scraped content to correct order
* Remove duplicates
* Insert missing entries

---

# Phase 6 — Logging & Debugging

Agent must output structured logs:

```text
[INFO] Arc 6: 54 chapters detected
[WARNING] Duplicate detected: Chapter 12
[ERROR] Missing: Prologue
[FIX] Inserted Prologue at position 0
[FIX] Removed duplicate Chapter 12
```

---

# Phase 7 — Final Validation Checklist

Before EPUB export:

* [ ] All chapters present
* [ ] No duplicates
* [ ] Order matches website exactly
* [ ] Prologue present (if exists)
* [ ] Interludes correctly placed
* [ ] EPUB ToC matches structure
* [ ] Text formatting preserved

---

# Core Rule (Non-Negotiable)

The website is the **single source of truth**.

The agent must **never infer order** — only replicate it.

---