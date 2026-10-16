from fastapi import FastAPI, HTTPException, Depends, Header
from langchain_google_genai.chat_models import GoogleAPIError
from agent import run_agent
from schemas import Answer, ChatRequest
import os
import secrets


app = FastAPI()

def require_api_secret(x_api_key: str | None = Header(default=None)):
    expected = os.environ["API_SECRET"]
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="unauthorized")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", dependencies=[Depends(require_api_secret)])
def chat(request: ChatRequest) -> Answer:
    try:
        return run_agent(request.message)
    except GoogleAPIError:
        raise HTTPException(status_code=503, detail="The AI model is busy right now. Try again in a minute.")



