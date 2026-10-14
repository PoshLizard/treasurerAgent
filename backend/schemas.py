from pydantic import BaseModel, Field

class Answer(BaseModel):
    """A researched answer to the treasurer's question"""
    summary: str = Field(description="The answer to the treasurer's question, based on the sources")
    sources: list[str] = Field(description="URLs returned by tools that support the answer. Empty list if no tool returned a URL")

class ChatRequest(BaseModel):
    message: str