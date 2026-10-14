import html
import os
import re

import requests
from firecrawl import Firecrawl, FirecrawlError
from langchain.tools import tool

firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

MAX_RESULTS = 3            # each scraped result costs 1 Firecrawl credit
MAX_CHARS_PER_PAGE = 3000  # about 750 tokens per page

# Matches "<source" or "</source" in scraped text, so a page can't fake its own source tag
SOURCE_TAG = re.compile(r"<(/?)source", re.IGNORECASE)


def _wrap_source(url: str, title: str | None, text: str) -> str:
    """Wrap one page in a <source> tag so the model can tell web content apart from instructions."""
    text = SOURCE_TAG.sub(r"&lt;\1source", text[:MAX_CHARS_PER_PAGE])
    return f'<source url="{html.escape(url)}" title="{html.escape(title or "")}">\n{text}\n</source>'


@tool
def research_web(query: str) -> str:
    """Search the web and read the top results. Use this for anything that needs current
    information: funding sources and grants, conference travel funding, fundraising ideas,
    vendor or venue prices, university pages, or what an unfamiliar receipt item code means.
    Returns each page's URL, title and main text inside <source> tags."""
    try:
        results = firecrawl.search(
            query,
            limit=MAX_RESULTS,
            scrape_options={"formats": ["markdown"], "only_main_content": True},
        )
    except (FirecrawlError, requests.RequestException) as e:
        return f"Web search failed: {e}"

    pages = []
    for item in results.web or []:
        if hasattr(item, "markdown"):  # scraped page (Document): URL lives in metadata
            meta = item.metadata
            url, title, text = meta.source_url or meta.url, meta.title, item.markdown or ""
        else:                          # plain search hit (SearchResultWeb)
            url, title, text = item.url, item.title, item.description or ""
        pages.append(_wrap_source(url, title, text))

    return "\n\n".join(pages) or "No results found."
