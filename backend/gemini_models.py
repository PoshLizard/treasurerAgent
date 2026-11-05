# On the free tier, flash-lite allows 15 requests a minute and 500 a day, while flash allows only
# 5 and 20. Receipts use flash-lite: it reads them as accurately (see evals/) in about 4 s instead
# of 25. The fallback is a different model with its own allowance, so it still answers when the
# primary is busy or at its limit.
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"

# Research is a multi-step process (search, open pages, follow sign-up links) that flash follows
# better than flash-lite. Each flash model has its own 20-a-day allowance, and one question makes
# 5 to 8 calls, so the chain ends on flash-lite instead of failing once they're used up.
# 3.8 is the newest, but on 2026-11-04 it returned 503 (high demand) on every call, so 3.6 goes first.
RESEARCH_MODELS = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3-flash-preview", PRIMARY_MODEL, FALLBACK_MODEL]
