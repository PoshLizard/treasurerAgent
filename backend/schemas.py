from pydantic import BaseModel, Field

class Answer(BaseModel):
    """A researched answer for treasurer fundraising ideas"""
    summary: str = Field(description="A summary of the researched fundraising ideas")
    sources: list[str] = Field(description="URLs returned by tools that support the answer. Empty list if no tool returned a URL")

class ChatRequest(BaseModel):
    message: str