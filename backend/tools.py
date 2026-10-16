import html
import os
import re

import requests
from firecrawl import Firecrawl, FirecrawlError
from langchain.tools import tool, ToolRuntime

firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

MAX_RESULTS = 3            # each scraped result costs 1 Firecrawl credit
MAX_CHARS_PER_PAGE = 3000  # about 750 tokens per search result
MAX_CHARS_PER_READ = 8000  # read_page is a deliberate deep read, so it gets more room
MAX_LINKS_PER_PAGE = 40

# Login walls and reposts: their scraped text is rarely useful and never the official page
SKIP_DOMAINS = ["facebook.com", "instagram.com", "pinterest.com", "tiktok.com"]

# Matches "<source" or "</source" in scraped text, so a page can't fake its own source tag
SOURCE_TAG = re.compile(r"<(/?)source", re.IGNORECASE)


def _wrap_source(url: str, title: str | None, text: str) -> str:
    """Wrap one page in a <source> tag so the model can tell web content apart from instructions."""
    text = SOURCE_TAG.sub(r"&lt;\1source", text)
    return f'<source url="{html.escape(url)}" title="{html.escape(title or "")}">\n{text}\n</source>'


def _is_broken(meta) -> bool:
    return bool(meta and meta.status_code and meta.status_code >= 400)


@tool
def research_web(query: str) -> str:
    """Search the web and read the top results. Use this for anything that needs current
    information: funding sources and grants, conference travel funding, fundraising ideas,
    vendor or venue prices, university pages, or what an unfamiliar receipt item code means.
    Takes a search query, not a URL: to open a specific page, use read_page.
    Returns each page's URL, title and main text inside <source> tags."""
    try:
        results = firecrawl.search(
            query,
            limit=MAX_RESULTS,
            exclude_domains=SKIP_DOMAINS,
            scrape_options={"formats": ["markdown"], "only_main_content": True},
        )
    except (FirecrawlError, requests.RequestException) as e:
        return f"Web search failed: {e}"

    pages = []
    for item in results.web or []:
        if hasattr(item, "markdown"):  # scraped page (Document): URL lives in metadata
            meta = item.metadata
            if _is_broken(meta):
                continue
            url, title, text = meta.source_url or meta.url, meta.title, item.markdown or ""
        else:                          # plain search hit (SearchResultWeb)
            url, title, text = item.url, item.title, item.description or ""
        pages.append(_wrap_source(url, title, text[:MAX_CHARS_PER_PAGE]))

    if not pages:
        return "No results found."
    # Models follow hints in the latest tool result more reliably than the system prompt
    hint = "Next step: call read_page on the most relevant official page above to find its sign-up or application link."
    return "\n\n".join(pages) + "\n\n" + hint


@tool
def read_page(url: str, runtime: ToolRuntime) -> str:
    """Open one web page and read its full text and the links on it. Use this to open an
    official program page, or to follow a "Sign up", "Register" or "Apply" link from an
    earlier result, so you can confirm the page works before giving it to the treasurer.
    Only URLs that appeared in earlier results or the user's message can be opened."""
    # Guardrail: the model can only open URLs it was shown. Otherwise a malicious page could
    # tell it to visit a URL with conversation data stuffed into it, leaking that data.
    seen = html.unescape(" ".join(
        str(m.content) for m in runtime.state["messages"] if m.type in ("human", "tool")
    ))
    if url not in seen:
        return "Can't open that URL: only URLs from earlier results or the user's message are allowed."

    try:
        page = firecrawl.scrape(url, formats=["markdown", "links"], only_main_content=True)
    except (FirecrawlError, requests.RequestException) as e:
        return f"Couldn't open the page: {e}"

    meta = page.metadata
    if _is_broken(meta):
        return f"The page returned HTTP {meta.status_code}, so it's broken or gone. Don't cite it."

    links = "\n".join((page.links or [])[:MAX_LINKS_PER_PAGE])
    text = f"{(page.markdown or '')[:MAX_CHARS_PER_READ]}\n\nLinks on this page:\n{links}"
    return _wrap_source((meta and (meta.source_url or meta.url)) or url, meta and meta.title, text)
