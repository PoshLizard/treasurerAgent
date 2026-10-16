from pydantic import BaseModel, Field

class Link(BaseModel):
    """A page the treasurer can act on"""
    label: str = Field(description="What the page is for, e.g. 'Panda Express fundraiser sign-up'")
    url: str = Field(description="URL returned by a tool")

class Answer(BaseModel):
    """A researched answer to the treasurer's question"""
    summary: str = Field(description="The answer to the treasurer's question, based on the sources")
    action_links: list[Link] = Field(description="Pages where the treasurer can take the next step: sign-up or registration forms, applications, order pages. Only URLs returned by tools. Empty list if none")
    sources: list[str] = Field(description="URLs returned by tools that support the answer. Empty list if no tool returned a URL")

class ChatRequest(BaseModel):
    message: str