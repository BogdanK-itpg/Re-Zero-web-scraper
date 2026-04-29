Create a custom web scraper for **[https://witchculttranslation.com/](https://witchculttranslation.com/)** that downloads story text and compiles it into a properly structured **.epub** file.

## Objective

Build an autonomous scraper that navigates the site's nested reading hierarchy and extracts chapters in correct reading order, then exports them into a clean EPUB ebook.

## Website Structure

The site uses a hierarchical reading tree:

* **Arc** = top-level story container
* **Phase** = optional subdivision inside an arc
* **Chapter** = final content page containing actual story text

Navigation path:

**Home / Table of Contents → Arc → Phase (if exists) → Chapter → Text Content**

## Required Agent Behavior

### 1. Discover Content

Start from:

[https://witchculttranslation.com/](https://witchculttranslation.com/)

Locate the main Table of Contents or Arc index pages.

Identify all available arcs.

### 2. Traverse Hierarchy

For each arc:

* Open arc page
* Detect whether phases exist

If phases exist:

* Iterate phases in ascending numeric order
* Inside each phase, collect chapter links in ascending order

If no phases exist:

* Collect chapter links directly from arc page in ascending order

### 3. Chapter Extraction

For each chapter page:

Extract:

* Chapter title
* Arc number/title
* Phase number/title (if any)
* Full translated story text
* Optional translator notes if clearly separated
* Chapter number if present

Ignore:

* Header
* Footer
* Sidebar widgets
* Ads
* Comment section
* Related posts
* Navigation clutter

### 4. Ordering Rules

Maintain strict reading order:

* Arc 1 before Arc 2
* Within arc: Phase 1 before Phase 2
* Within phase: Chapter 1 before Chapter 2

If numbering missing:

* Use chapter titles
* Use page order from arc index
* Use previous/next chapter links

### 5. Duplicate Protection

Avoid duplicate chapters caused by:

* multiple category links
* mirrored links
* navigation links
* repeated homepage references

Use canonical URL deduplication.

### 6. EPUB Output

Generate a valid EPUB file with:

Metadata:

* Title: Re:Zero Web Novel (or selected Arc title)
* Author: Tappei Nagatsuki
* Source: Witch Cult Translations

Table of Contents:

* Arc
* Phase
* Chapter titles

Formatting:

* One XHTML file per chapter
* Proper headings
* Paragraph spacing preserved
* UTF-8 encoding
* Clean HTML only

### 7. User Modes

Support these modes:

#### Full Library

Scrape all arcs and export one EPUB.

#### Single Arc

Example:
Arc 7 only

#### Arc Range

Example:
Arc 5 to Arc 8

#### Specific Chapter

Example:
Arc 6 Chapter 23

#### Latest Content

Detect newest available chapter and export only new chapters.

### 8. Robustness Rules

Handle:

* relative URLs
* inconsistent numbering
* title-based slugs
* missing phase labels
* pagination
* retries on timeout
* rate limiting with respectful delays

### 9. Recommended Tech Stack

Use Python with:

* requests / httpx
* BeautifulSoup or lxml
* ebooklib (for EPUB)
* asyncio optional for speed

### 10. Output Example

```text
ReZero_Arc_7.epub
ReZero_Arc_1_to_8.epub
ReZero_Full_Web_Novel.epub
```

### 11. Important Scraping Logic

When parsing chapter pages, prioritize main article containers such as:

* `<article>`
* `.entry-content`
* `.post-content`
* `.content`

### 12. Final Deliverable

Produce reusable scraper code with CLI usage:

```bash
python scraper.py --arc 7
python scraper.py --all
python scraper.py --latest
python scraper.py --range 5 8
```
