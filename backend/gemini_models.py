# On the free tier, flash-lite allows 15 requests a minute and 500 a day, while flash allows only
# 5 and 20, and a research question alone makes several calls. The fallback is a different model
# with its own allowance, so it still answers when the primary is busy or at its limit.
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
