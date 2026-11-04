from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError
from agent import run_agent
from receipt_checks import check_receipt
from receipt_store import duplicate_issues, get_receipt, list_receipts, photo_url, save_receipt
from receipts import extract_receipt
from schemas import Answer, ChatRequest, PhotoLink, ReceiptDetail, ReceiptResult, ReceiptSummary
from uuid import UUID
import os
import psycopg
import requests
import secrets


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_IMAGE_BYTES = 7 * 1024 * 1024

MODEL_BUSY = "The AI model is busy right now. Try again in a minute."
# Only reached once the fallback model hits its limit too. A daily quota can take hours to reset
MODEL_LIMIT_REACHED = "The AI model's usage limit was reached. Try again later."

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
        raise HTTPException(status_code=503, detail=MODEL_BUSY)
    except GoogleRateLimitError:
        raise HTTPException(status_code=503, detail=MODEL_LIMIT_REACHED)

@app.post("/receipts", dependencies=[Depends(require_api_secret)])
def upload_receipt(image: UploadFile) -> ReceiptResult:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, WebP or HEIC image.")

    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="That image is too large. The limit is 7 MB.")

    try:
        receipt = extract_receipt(data, image.content_type)
    except GoogleAPIError:
        raise HTTPException(status_code=503, detail=MODEL_BUSY)
    except GoogleRateLimitError:
        raise HTTPException(status_code=503, detail=MODEL_LIMIT_REACHED)
    if receipt is None:
        raise HTTPException(status_code=422, detail="Couldn't read that image. Try a clearer photo.")

    try:
        issues = check_receipt(receipt) + duplicate_issues(receipt)
        receipt_id = save_receipt(receipt, issues, data, image.content_type)
    except (psycopg.Error, requests.RequestException):
        raise HTTPException(status_code=503, detail="Couldn't save that receipt. Try again in a minute.")
    return ReceiptResult(id=receipt_id, receipt=receipt, issues=issues)

@app.get("/receipts", dependencies=[Depends(require_api_secret)])
def get_receipts() -> list[ReceiptSummary]:
    try:
        return list_receipts()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Couldn't load saved receipts. Try again in a minute.")

# Typed as UUID, so FastAPI answers 422 for anything else before the database sees it
@app.get("/receipts/{receipt_id}", dependencies=[Depends(require_api_secret)])
def get_one_receipt(receipt_id: UUID) -> ReceiptDetail:
    try:
        detail = get_receipt(receipt_id)
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Couldn't load that receipt. Try again in a minute.")
    if detail is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return detail

# A fresh link on every request, so a page left open never holds an expired one
@app.get("/receipts/{receipt_id}/photo", dependencies=[Depends(require_api_secret)])
def get_photo_link(receipt_id: UUID) -> PhotoLink:
    try:
        url = photo_url(receipt_id)
    except (psycopg.Error, requests.RequestException):
        raise HTTPException(status_code=503, detail="Couldn't load the photo. Try again in a minute.")
    if url is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return PhotoLink(url=url)
