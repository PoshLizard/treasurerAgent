from langchain.tools import tool

@tool
def fundraisingResearch(query: str) -> str:
    """Search the web for best fundraising ideas for an Asian and Pacific Islander Student Association"""
    return f"Results for: {query}"