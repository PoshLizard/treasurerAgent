from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain.tools import tool
from pydantic import BaseModel
load_dotenv()

currentModel = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)

class Answer(BaseModel):
    summary: str
    sources: list[str]

@tool
def fundraisingResearch(query: str) -> str:
    """Search the web for best fundraising ideas for an Asian and Pacific Islander Student Association"""
    return f"Results for: {query}"



agent = create_agent(model= currentModel, 
                     tools=[fundraisingResearch], 
                     system_prompt="You are a helpful assistant to the treasurer of the Asian and Pacific Islander Student Association.",
                     response_format=Answer,
                     middleware=[ModelFallbackMiddleware(ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite"))]
                    )

if __name__ == "__main__":
    result = agent.invoke({"messages": [{"role": "user", "content": "What are some fundraising ideas for an Asian and Pacific Islander Student Association?"}]})
    print(result["structured_response"])


