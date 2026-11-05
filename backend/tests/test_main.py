import json
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import httpx
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


def gemini_timed_out(*args, **kwargs):
    # The client gives up on a model that hangs (one took 5 minutes just to return a 503), and the
    # error comes from httpx, not from Gemini's own error classes
    raise httpx.ReadTimeout("timed out")


MODEL_FAILURES = [
    (gemini_outage, "The AI model is busy right now. Try again in a minute."),
    (gemini_rate_limited, "The AI model's usage limit was reached. Try again later."),
    (gemini_timed_out, "The AI model is busy right now. Try again in a minute."),
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
    ("GET", f"/receipts/{uuid4()}/photo"), ("PUT", f"/receipts/{uuid4()}"), ("DELETE", f"/receipts/{uuid4()}"),
    ("POST", "/chat/stream"),
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


# Editing and deleting

def detail_of(receipt, issues):
    return ReceiptDetail(id=RECEIPT_ID, receipt=receipt, issues=issues, status="needs_review",
                         created_at=datetime(2026, 11, 2, tzinfo=timezone.utc))


@pytest.fixture
def edits(monkeypatch):
    """Make every edit step succeed without Supabase. Returns the list of saved edits."""
    saved_edits = []

    def update_receipt(receipt_id, receipt, issues):
        saved_edits.append({"id": receipt_id, "receipt": receipt, "issues": issues})
        return receipt_id == RECEIPT_ID

    monkeypatch.setattr(main, "update_receipt", update_receipt)
    monkeypatch.setattr(main, "duplicate_issues", lambda receipt, ignore_id=None: [])
    monkeypatch.setattr(main, "get_receipt", lambda receipt_id: detail_of(saved_edits[-1]["receipt"], saved_edits[-1]["issues"]))
    return saved_edits


def test_edit_saves_the_corrections_and_rechecks_them(edits):
    corrected = RECEIPT.model_copy(update={"merchant": "DOLLAR TREE #1678", "total": RECEIPT.total + 1})

    response = client.put(f"/receipts/{RECEIPT_ID}", headers=AUTH, json=corrected.model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["receipt"]["merchant"] == "DOLLAR TREE #1678"
    # The math is checked again, so a correction that doesn't add up is still flagged
    assert edits[0]["issues"] == ["Subtotal, tax and tip add up to 1.25, but the total says 2.25."]
    assert response.json()["issues"] == edits[0]["issues"]


def test_edit_checks_for_duplicates_other_than_itself(monkeypatch, edits):
    ignored = []

    def duplicate_issues(receipt, ignore_id=None):
        ignored.append(ignore_id)
        return []

    monkeypatch.setattr(main, "duplicate_issues", duplicate_issues)
    client.put(f"/receipts/{RECEIPT_ID}", headers=AUTH, json=RECEIPT.model_dump(mode="json"))
    assert ignored == [RECEIPT_ID]


def test_editing_a_missing_receipt_is_404(edits):
    response = client.put(f"/receipts/{uuid4()}", headers=AUTH, json=RECEIPT.model_dump(mode="json"))
    assert response.status_code == 404


def test_an_edit_without_items_is_rejected(edits):
    response = client.put(f"/receipts/{RECEIPT_ID}", headers=AUTH, json={"merchant": "DOLLAR TREE"})
    assert response.status_code == 422
    assert edits == []


@pytest.mark.parametrize("error", [psycopg.OperationalError("down"), requests.ConnectionError("down")])
def test_edit_when_storage_is_down(monkeypatch, edits, error):
    monkeypatch.setattr(main, "update_receipt", Mock(side_effect=error))
    response = client.put(f"/receipts/{RECEIPT_ID}", headers=AUTH, json=RECEIPT.model_dump(mode="json"))
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't save your changes. Try again in a minute."


def test_delete(monkeypatch):
    deleted = []

    def delete_receipt(receipt_id):
        deleted.append(receipt_id)
        return True

    monkeypatch.setattr(main, "delete_receipt", delete_receipt)
    response = client.delete(f"/receipts/{RECEIPT_ID}", headers=AUTH)
    assert response.status_code == 204
    assert deleted == [RECEIPT_ID]


def test_deleting_a_missing_receipt_is_404(monkeypatch):
    monkeypatch.setattr(main, "delete_receipt", lambda receipt_id: False)
    assert client.delete(f"/receipts/{uuid4()}", headers=AUTH).status_code == 404


@pytest.mark.parametrize("error", [psycopg.OperationalError("down"), requests.ConnectionError("down")])
def test_delete_when_storage_is_down(monkeypatch, error):
    monkeypatch.setattr(main, "delete_receipt", Mock(side_effect=error))
    response = client.delete(f"/receipts/{RECEIPT_ID}", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't delete that receipt. Try again in a minute."


# Chat

def test_chat_returns_the_agent_answer(monkeypatch):
    answer = Answer(summary="Try a restaurant fundraiser.", action_links=[], sources=[])
    monkeypatch.setattr(main, "run_agent", lambda message: answer)

    response = client.post("/chat", headers=AUTH, json={"message": "fundraising ideas?"})

    assert response.status_code == 200
    assert response.json() == answer.model_dump(mode="json")


def server_sent_events(response):
    """Parse a text/event-stream body into the JSON events it carries."""
    return [json.loads(chunk.removeprefix("data: ")) for chunk in response.text.split("\n\n") if chunk]


def test_chat_stream_sends_events_as_server_sent_events(monkeypatch):
    events = [{"type": "step", "text": "Searching the web for “grants”"},
              {"type": "answer", "answer": {"summary": "Apply.", "action_links": [], "sources": []}}]
    monkeypatch.setattr(main, "stream_agent", lambda message: iter(events))

    response = client.post("/chat/stream", headers=AUTH, json={"message": "grants?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert server_sent_events(response) == events


@pytest.mark.parametrize("failure, detail", MODEL_FAILURES)
def test_model_failure_mid_stream_becomes_an_error_event(monkeypatch, failure, detail):
    # The 200 status is already sent once streaming starts, so the failure has to travel as an event
    def stream_agent(message):
        yield {"type": "step", "text": "Searching the web for “grants”"}
        failure()

    monkeypatch.setattr(main, "stream_agent", stream_agent)
    events = server_sent_events(client.post("/chat/stream", headers=AUTH, json={"message": "grants?"}))
    assert events == [{"type": "step", "text": "Searching the web for “grants”"}, {"type": "error", "detail": detail}]


def test_unexpected_failure_mid_stream_becomes_an_error_event(monkeypatch):
    def stream_agent(message):
        raise RuntimeError("bug")
        yield  # makes this a generator

    monkeypatch.setattr(main, "stream_agent", stream_agent)
    events = server_sent_events(client.post("/chat/stream", headers=AUTH, json={"message": "grants?"}))
    assert events == [{"type": "error", "detail": "Something went wrong. Try asking again."}]


@pytest.mark.parametrize("failure, detail", MODEL_FAILURES)
def test_model_failure_on_chat_explains_itself(monkeypatch, failure, detail):
    monkeypatch.setattr(main, "run_agent", failure)
    response = client.post("/chat", headers=AUTH, json={"message": "fundraising ideas?"})
    assert response.status_code == 503
    assert response.json()["detail"] == detail
