from dotenv import load_dotenv
load_dotenv()  # before reading the Supabase settings below

import os
from uuid import UUID, uuid4

import psycopg
import requests
from psycopg.rows import dict_row

from schemas import Receipt, ReceiptDetail, ReceiptSummary

DATABASE_URL = os.environ["DATABASE_URL"]
STORAGE_URL = f"{os.environ['SUPABASE_URL'].rstrip('/')}/storage/v1"
BUCKET_URL = f"{STORAGE_URL}/object/receipts"
# This key bypasses Supabase's access rules, so it must only ever exist on the backend
STORAGE_HEADERS = {"apikey": os.environ["SUPABASE_SECRET_KEY"]}

FILE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
                   "image/heic": "heic", "image/heif": "heif"}
MAX_LISTED_RECEIPTS = 50
# The browser follows the link the moment it gets it, so a minute is plenty, and a copied
# link stops working almost right away
SIGNED_URL_SECONDS = 60


def _upload_image(path: str, image: bytes, mime_type: str) -> None:
    response = requests.post(f"{BUCKET_URL}/{path}", data=image, timeout=30,
                             headers={**STORAGE_HEADERS, "Content-Type": mime_type})
    response.raise_for_status()


def _delete_image(path: str) -> None:
    requests.delete(f"{BUCKET_URL}/{path}", headers=STORAGE_HEADERS, timeout=30).raise_for_status()


def _signed_image_url(path: str) -> str:
    """Return a link to a photo that the browser can load without the secret key, until it expires."""
    response = requests.post(f"{STORAGE_URL}/object/sign/receipts/{path}", json={"expiresIn": SIGNED_URL_SECONDS},
                             headers=STORAGE_HEADERS, timeout=30)
    response.raise_for_status()
    return f"{STORAGE_URL}{response.json()['signedURL']}"


def duplicate_issues(receipt: Receipt) -> list[str]:
    """Flag a receipt matching a saved one, so one purchase can't be reimbursed twice.

    This warns instead of blocking, because two identical purchases on one day can be real."""
    if not receipt.merchant or receipt.purchase_date is None or receipt.total is None:
        return []

    with psycopg.connect(DATABASE_URL) as conn:
        match = conn.execute(
            """select 1 from receipts
               where lower(merchant) = lower(%s) and purchase_date = %s and total = %s
               limit 1""",
            (receipt.merchant, receipt.purchase_date, receipt.total),
        ).fetchone()

    if match is None:
        return []
    return ["Possible duplicate: a receipt with the same store, date and total is already saved."]


def save_receipt(receipt: Receipt, issues: list[str], image: bytes, mime_type: str) -> UUID:
    """Save the photo and the receipt's data. Every receipt starts as needs_review, because
    only the treasurer can approve one, even if every check passed."""
    receipt_id = uuid4()
    image_path = f"{receipt_id}.{FILE_EXTENSIONS[mime_type]}"
    _upload_image(image_path, image, mime_type)

    try:
        # A transaction: both tables save together, or neither does
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(
                """insert into receipts (id, merchant, purchase_date, subtotal, tax, tip, total, issues, image_path)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (receipt_id, receipt.merchant, receipt.purchase_date, receipt.subtotal,
                 receipt.tax, receipt.tip, receipt.total, issues, image_path),
            )
            conn.cursor().executemany(
                """insert into line_items (receipt_id, position, raw_text, item_code, quantity, unit_price, line_total)
                   values (%s, %s, %s, %s, %s, %s, %s)""",
                [(receipt_id, position, item.raw_text, item.item_code, item.quantity, item.unit_price, item.line_total)
                 for position, item in enumerate(receipt.items)],
            )
    except psycopg.Error:
        _delete_image(image_path)  # the bucket and database can't share a transaction
        raise

    return receipt_id


def list_receipts() -> list[ReceiptSummary]:
    """Return the most recently saved receipts."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            """select id, merchant, purchase_date, total, status, issues, created_at
               from receipts order by created_at desc limit %s""",
            (MAX_LISTED_RECEIPTS,),
        ).fetchall()
    return [ReceiptSummary(**row) for row in rows]


def get_receipt(receipt_id: UUID) -> ReceiptDetail | None:
    """Return one saved receipt with its line items, or None if it doesn't exist."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            """select id, merchant, purchase_date, subtotal, tax, tip, total, issues, status, created_at
               from receipts where id = %s""",
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        items = conn.execute(
            """select raw_text, item_code, quantity, unit_price, line_total
               from line_items where receipt_id = %s order by position""",
            (receipt_id,),
        ).fetchall()

    receipt = Receipt(items=items, **{field: row[field] for field in
                                      ("merchant", "purchase_date", "subtotal", "tax", "tip", "total")})
    return ReceiptDetail(id=row["id"], receipt=receipt, issues=row["issues"], status=row["status"],
                         created_at=row["created_at"])


def photo_url(receipt_id: UUID) -> str | None:
    """Return a fresh, short-lived link to a receipt's photo, or None if the receipt doesn't exist."""
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("select image_path from receipts where id = %s", (receipt_id,)).fetchone()
    return None if row is None else _signed_image_url(row[0])
