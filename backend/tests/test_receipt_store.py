from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
import requests

import receipt_store
from receipt_store import duplicate_issues, get_receipt, list_receipts, save_receipt
from schemas import LineItem, Receipt


class FakeConnection:
    """Stands in for a psycopg connection: records each query and returns rows queued by the test."""

    def __init__(self):
        self.rows = []     # one entry per fetchone() or fetchall(), in order
        self.queries = []  # (sql, params) for every query run

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        return self  # psycopg returns a cursor here; this fake is its own cursor

    def cursor(self):
        return self

    def executemany(self, sql, params_seq):
        self.queries.append((sql, list(params_seq)))

    def fetchone(self):
        return self.rows.pop(0)

    def fetchall(self):
        return self.rows.pop(0)

    def params_of(self, sql_fragment):
        return next(params for sql, params in self.queries if sql_fragment in sql)


class FakeBucket:
    """Stands in for the Supabase Storage bucket."""

    def __init__(self):
        self.files = {}

    def upload(self, path, image, mime_type):
        self.files[path] = (image, mime_type)

    def delete(self, path):
        del self.files[path]

    def signed_url(self, path):
        return f"https://signed.test/{path}"


@pytest.fixture
def db(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: connection)
    return connection


@pytest.fixture
def bucket(monkeypatch):
    fake = FakeBucket()
    monkeypatch.setattr(receipt_store, "_upload_image", fake.upload)
    monkeypatch.setattr(receipt_store, "_delete_image", fake.delete)
    monkeypatch.setattr(receipt_store, "_signed_image_url", fake.signed_url)
    return fake


def database_down(*args, **kwargs):
    raise psycopg.OperationalError("connection refused")


def receipt(**overrides) -> Receipt:
    values = {
        "merchant": "DOLLAR TREE",
        "purchase_date": "2024-09-19",
        "items": [
            LineItem(raw_text="RING POP", item_code=None, quantity="1", unit_price=None, line_total="1.25"),
            LineItem(raw_text="KIT KAT", item_code="0034000", quantity="2", unit_price="1.25", line_total="2.50"),
        ],
        "subtotal": "3.75",
        "tax": "0",
        "tip": None,
        "total": "3.75",
    }
    return Receipt(**(values | overrides))


# Duplicate detection

@pytest.mark.parametrize("missing", [{"merchant": None}, {"purchase_date": None}, {"total": None}])
def test_duplicate_check_needs_store_date_and_total(db, missing):
    assert duplicate_issues(receipt(**missing)) == []
    assert db.queries == []  # nothing to match on, so it doesn't ask the database


def test_matching_saved_receipt_is_flagged(db):
    db.rows.append((1,))

    issues = duplicate_issues(receipt())

    # No "saved on" date: the server runs in UTC, so evening saves would show tomorrow's date
    assert issues == ["Possible duplicate: a receipt with the same store, date and total is already saved."]
    assert db.params_of("from receipts") == ("DOLLAR TREE", date(2024, 9, 19), Decimal("3.75"))


def test_no_match_means_no_duplicate_issue(db):
    db.rows.append(None)
    assert duplicate_issues(receipt()) == []


# Saving

def test_save_stores_the_photo_and_every_line_item_in_order(db, bucket):
    receipt_id = save_receipt(receipt(), ["Possible duplicate"], b"photo", "image/jpeg")

    image_path = f"{receipt_id}.jpg"
    assert bucket.files == {image_path: (b"photo", "image/jpeg")}

    saved = db.params_of("insert into receipts")
    assert saved[0] == receipt_id
    assert saved[1:3] == ("DOLLAR TREE", date(2024, 9, 19))
    assert saved[-2:] == (["Possible duplicate"], image_path)

    rows = db.params_of("insert into line_items")
    assert [(row[1], row[2]) for row in rows] == [(0, "RING POP"), (1, "KIT KAT")]
    assert all(row[0] == receipt_id for row in rows)


@pytest.mark.parametrize("mime_type, extension", [("image/png", "png"), ("image/heic", "heic")])
def test_photo_type_sets_the_file_extension(db, bucket, mime_type, extension):
    receipt_id = save_receipt(receipt(), [], b"photo", mime_type)
    assert list(bucket.files) == [f"{receipt_id}.{extension}"]


def test_failed_database_save_removes_the_photo(monkeypatch, bucket):
    monkeypatch.setattr(psycopg, "connect", database_down)

    with pytest.raises(psycopg.OperationalError):
        save_receipt(receipt(), [], b"photo", "image/jpeg")

    assert bucket.files == {}  # no orphaned photo with no receipt pointing at it


def test_failed_upload_never_touches_the_database(monkeypatch, db, bucket):
    monkeypatch.setattr(receipt_store, "_upload_image", Mock(side_effect=requests.ConnectionError()))

    with pytest.raises(requests.ConnectionError):
        save_receipt(receipt(), [], b"photo", "image/jpeg")

    assert db.queries == []


# Reading

def test_list_returns_saved_receipts(db):
    receipt_id = uuid4()
    db.rows.append([{"id": receipt_id, "merchant": "DOLLAR TREE", "purchase_date": date(2024, 9, 19),
                     "total": Decimal("3.75"), "status": "needs_review", "issues": [],
                     "created_at": datetime(2026, 11, 2, tzinfo=timezone.utc)}])

    [summary] = list_receipts()

    assert summary.id == receipt_id
    assert summary.merchant == "DOLLAR TREE"
    assert db.params_of("from receipts") == (receipt_store.MAX_LISTED_RECEIPTS,)


def test_get_receipt_returns_none_when_it_does_not_exist(db, bucket):
    db.rows.append(None)
    assert get_receipt(uuid4()) is None


def test_get_receipt_rebuilds_the_receipt_with_a_photo_link(db, bucket):
    receipt_id = uuid4()
    db.rows.append({"id": receipt_id, "merchant": "DOLLAR TREE", "purchase_date": date(2024, 9, 19),
                    "subtotal": Decimal("3.75"), "tax": Decimal("0"), "tip": None, "total": Decimal("3.75"),
                    "issues": ["Possible duplicate"], "status": "needs_review",
                    "created_at": datetime(2026, 11, 2, tzinfo=timezone.utc), "image_path": f"{receipt_id}.jpg"})
    db.rows.append([
        {"raw_text": "RING POP", "item_code": None, "quantity": Decimal("1"), "unit_price": None, "line_total": Decimal("1.25")},
        {"raw_text": "KIT KAT", "item_code": "0034000", "quantity": Decimal("2"), "unit_price": Decimal("1.25"), "line_total": Decimal("2.50")},
    ])

    detail = get_receipt(receipt_id)

    assert detail.id == receipt_id
    assert detail.receipt == receipt()
    assert detail.issues == ["Possible duplicate"]
    assert detail.status == "needs_review"
    assert detail.image_url == f"https://signed.test/{receipt_id}.jpg"
    assert "order by position" in db.queries[1][0]  # items come back in printed order


# Talking to Supabase Storage

def fake_response(json_body=None, status_error=None):
    response = Mock()
    response.json.return_value = json_body
    response.raise_for_status.side_effect = status_error
    return response


def test_upload_sends_the_photo_with_its_type(monkeypatch):
    post = Mock(return_value=fake_response())
    monkeypatch.setattr(requests, "post", post)

    receipt_store._upload_image("abc.png", b"photo", "image/png")

    assert post.call_args.args[0] == "https://project.supabase.test/storage/v1/object/receipts/abc.png"
    assert post.call_args.kwargs["data"] == b"photo"
    assert post.call_args.kwargs["headers"] == {"apikey": "test-supabase-key", "Content-Type": "image/png"}


def test_storage_errors_are_raised(monkeypatch):
    monkeypatch.setattr(requests, "post", Mock(return_value=fake_response(status_error=requests.HTTPError("403"))))
    with pytest.raises(requests.HTTPError):
        receipt_store._upload_image("abc.png", b"photo", "image/png")


def test_signed_url_is_a_full_link_that_expires(monkeypatch):
    post = Mock(return_value=fake_response({"signedURL": "/object/sign/receipts/abc.jpg?token=t0k3n"}))
    monkeypatch.setattr(requests, "post", post)

    url = receipt_store._signed_image_url("abc.jpg")

    assert url == "https://project.supabase.test/storage/v1/object/sign/receipts/abc.jpg?token=t0k3n"
    assert post.call_args.args[0] == "https://project.supabase.test/storage/v1/object/sign/receipts/abc.jpg"
    assert post.call_args.kwargs["json"] == {"expiresIn": receipt_store.SIGNED_URL_SECONDS}
