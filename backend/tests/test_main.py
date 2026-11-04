from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
import requests
from fastapi.testclient import TestClient
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError

import main
from schemas import Answer, Receipt, ReceiptDetail, ReceiptSummary

client = TestClient(main.app)
AUTH = {"X-API-Key": "test-api-secret"}
RECEIPT_ID = uuid4()
RECEIPT = Receipt(merchant="DOLLAR TREE", purchase_date="2024-09-19",
                  items=[{"raw_text": "RING POP", "item_code": None, "quantity": "1", "unit_price": None, "line_total": "1.25"}],
                  subtotal="1.25", tax="0", tip=None, total="1.25")


def gemini_outage(*args, **kwargs):
    raise GoogleAPIError(503, {"error": {"message": "overloaded"}})


def gemini_rate_limited(*args, **kwargs):
    # A different error class from an outage: it doesn't inherit from GoogleAPIError
    raise GoogleRateLimitError("429 RESOURCE_EXHAUSTED")


MODEL_FAILURES = [
    (gemini_outage, "The AI model is busy right now. Try again in a minute."),
    (gemini_rate_limited, "The AI model's usage limit was reached. Try again later."),
]


def database_down(*args, **kwargs):
    raise psycopg.OperationalError("connection refused")


def upload(content=b"photo", content_type="image/jpeg"):
    return client.post("/receipts", headers=AUTH, files={"image": ("receipt", content, content_type)})


@pytest.fixture
def saved(monkeypatch):
    """Make every upload step succeed without Gemini or Supabase. Returns the list of saved receipts."""
    saved_receipts = []

    def save_receipt(receipt, issues, image, mime_type):
        saved_receipts.append({"receipt": receipt, "issues": issues, "image": image, "mime_type": mime_type})
        return RECEIPT_ID

    monkeypatch.setattr(main, "extract_receipt", lambda image, mime_type: RECEIPT)
    monkeypatch.setattr(main, "duplicate_issues", lambda receipt: [])
    monkeypatch.setattr(main, "save_receipt", save_receipt)
    return saved_receipts


def test_health_needs_no_key():
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("method, path", [
    ("POST", "/chat"), ("POST", "/receipts"), ("GET", "/receipts"), ("GET", f"/receipts/{uuid4()}"),
    ("GET", f"/receipts/{uuid4()}/photo"),
])
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_every_other_route_needs_the_api_key(method, path, headers):
    assert client.request(method, path, headers=headers).status_code == 401


# Uploading a receipt

def test_upload_returns_what_it_saved(saved):
    response = upload()

    assert response.status_code == 200
    assert response.json() == {"id": str(RECEIPT_ID), "receipt": RECEIPT.model_dump(mode="json"), "issues": []}
    assert saved[0]["image"] == b"photo"
    assert saved[0]["mime_type"] == "image/jpeg"


def test_upload_saves_and_returns_check_and_duplicate_issues(monkeypatch, saved):
    wrong_total = RECEIPT.model_copy(update={"total": RECEIPT.total + 1})
    monkeypatch.setattr(main, "extract_receipt", lambda image, mime_type: wrong_total)
    monkeypatch.setattr(main, "duplicate_issues", lambda receipt: ["Possible duplicate"])

    issues = upload().json()["issues"]

    assert issues == ["Subtotal, tax and tip add up to 1.25, but the total says 2.25.", "Possible duplicate"]
    assert saved[0]["issues"] == issues  # what the treasurer sees is what's stored


def test_unsupported_file_type_is_rejected(saved):
    response = upload(b"%PDF-1.7", "application/pdf")
    assert response.status_code == 415
    assert response.json()["detail"] == "Upload a JPEG, PNG, WebP or HEIC image."
    assert saved == []


def test_oversized_photo_is_rejected(saved):
    response = upload(b"x" * (main.MAX_IMAGE_BYTES + 1))
    assert response.status_code == 413
    assert saved == []


@pytest.mark.parametrize("failure, detail", MODEL_FAILURES)
def test_model_failure_on_upload_explains_itself(monkeypatch, saved, failure, detail):
    monkeypatch.setattr(main, "extract_receipt", failure)
    response = upload()
    assert response.status_code == 503
    assert response.json()["detail"] == detail
    assert saved == []


def test_unreadable_photo_asks_for_a_clearer_one(monkeypatch, saved):
    monkeypatch.setattr(main, "extract_receipt", lambda image, mime_type: None)
    response = upload()
    assert response.status_code == 422
    assert response.json()["detail"] == "Couldn't read that image. Try a clearer photo."
    assert saved == []


@pytest.mark.parametrize("error", [psycopg.OperationalError("down"), requests.ConnectionError("down")])
def test_storage_outage_asks_to_try_again(monkeypatch, saved, error):
    monkeypatch.setattr(main, "save_receipt", Mock(side_effect=error))
    response = upload()
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't save that receipt. Try again in a minute."


# Reading saved receipts

def test_list_receipts(monkeypatch):
    summary = ReceiptSummary(id=RECEIPT_ID, merchant="DOLLAR TREE", purchase_date="2024-09-19", total="1.25",
                             status="needs_review", issues=[], created_at=datetime(2026, 11, 2, tzinfo=timezone.utc))
    monkeypatch.setattr(main, "list_receipts", lambda: [summary])

    response = client.get("/receipts", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == [summary.model_dump(mode="json")]


def test_list_receipts_when_the_database_is_down(monkeypatch):
    monkeypatch.setattr(main, "list_receipts", database_down)
    assert client.get("/receipts", headers=AUTH).status_code == 503


def test_get_one_receipt(monkeypatch):
    detail = ReceiptDetail(id=RECEIPT_ID, receipt=RECEIPT, issues=[], status="needs_review",
                           created_at=datetime(2026, 11, 2, tzinfo=timezone.utc))
    monkeypatch.setattr(main, "get_receipt", lambda receipt_id: detail if receipt_id == RECEIPT_ID else None)

    response = client.get(f"/receipts/{RECEIPT_ID}", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == detail.model_dump(mode="json")


def test_missing_receipt_is_404(monkeypatch):
    monkeypatch.setattr(main, "get_receipt", lambda receipt_id: None)
    response = client.get(f"/receipts/{uuid4()}", headers=AUTH)
    assert response.status_code == 404
    assert response.json()["detail"] == "Receipt not found."


def test_malformed_receipt_id_never_reaches_the_database(monkeypatch):
    get_receipt = Mock()
    monkeypatch.setattr(main, "get_receipt", get_receipt)
    assert client.get("/receipts/not-a-uuid", headers=AUTH).status_code == 422
    get_receipt.assert_not_called()


def test_get_one_receipt_when_the_database_is_down(monkeypatch):
    monkeypatch.setattr(main, "get_receipt", database_down)
    response = client.get(f"/receipts/{RECEIPT_ID}", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't load that receipt. Try again in a minute."


# Photos: the page asks for a fresh link each time it shows one, so it never holds an expired link

def test_photo_link(monkeypatch):
    monkeypatch.setattr(main, "photo_url", lambda receipt_id: "https://signed.test/a.jpg" if receipt_id == RECEIPT_ID else None)
    response = client.get(f"/receipts/{RECEIPT_ID}/photo", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"url": "https://signed.test/a.jpg"}


def test_photo_link_for_a_missing_receipt_is_404(monkeypatch):
    monkeypatch.setattr(main, "photo_url", lambda receipt_id: None)
    assert client.get(f"/receipts/{uuid4()}/photo", headers=AUTH).status_code == 404


@pytest.mark.parametrize("error", [psycopg.OperationalError("down"), requests.ConnectionError("down")])
def test_photo_link_when_storage_is_down(monkeypatch, error):
    monkeypatch.setattr(main, "photo_url", Mock(side_effect=error))
    response = client.get(f"/receipts/{RECEIPT_ID}/photo", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't load the photo. Try again in a minute."


# Chat

def test_chat_returns_the_agent_answer(monkeypatch):
    answer = Answer(summary="Try a restaurant fundraiser.", action_links=[], sources=[])
    monkeypatch.setattr(main, "run_agent", lambda message: answer)

    response = client.post("/chat", headers=AUTH, json={"message": "fundraising ideas?"})

    assert response.status_code == 200
    assert response.json() == answer.model_dump(mode="json")


@pytest.mark.parametrize("failure, detail", MODEL_FAILURES)
def test_model_failure_on_chat_explains_itself(monkeypatch, failure, detail):
    monkeypatch.setattr(main, "run_agent", failure)
    response = client.post("/chat", headers=AUTH, json={"message": "fundraising ideas?"})
    assert response.status_code == 503
    assert response.json()["detail"] == detail
