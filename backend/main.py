from fastapi import FastAPI, HTTPException
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import BaseModel
from agent import agent, Answer

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest) -> Answer:
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": request.message}]}
        )
    except GoogleAPIError:
        raise HTTPException(status_code=503, detail="The AI model is busy right now. Try again in a minute.")
    return result["structured_response"]



