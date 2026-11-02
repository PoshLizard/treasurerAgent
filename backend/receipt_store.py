from dotenv import load_dotenv
load_dotenv()  # before reading the Supabase settings below

import os
from uuid import UUID, uuid4

import psycopg
import requests
from psycopg.rows import dict_row

from schemas import Receipt, ReceiptSummary

DATABASE_URL = os.environ["DATABASE_URL"]
BUCKET_URL = f"{os.environ['SUPABASE_URL'].rstrip('/')}/storage/v1/object/receipts"
# This key bypasses Supabase's access rules, so it must only ever exist on the backend
STORAGE_HEADERS = {"apikey": os.environ["SUPABASE_SECRET_KEY"]}

FILE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
                   "image/heic": "heic", "image/heif": "heif"}
MAX_LISTED_RECEIPTS = 50


def _upload_image(path: str, image: bytes, mime_type: str) -> None:
    response = requests.post(f"{BUCKET_URL}/{path}", data=image, timeout=30,
                             headers={**STORAGE_HEADERS, "Content-Type": mime_type})
    response.raise_for_status()


def _delete_image(path: str) -> None:
    requests.delete(f"{BUCKET_URL}/{path}", headers=STORAGE_HEADERS, timeout=30).raise_for_status()


def duplicate_issues(receipt: Receipt) -> list[str]:
    """Flag a receipt matching a saved one, so one purchase can't be reimbursed twice.

    This warns instead of blocking, because two identical purchases on one day can be real."""
    if not receipt.merchant or receipt.purchase_date is None or receipt.total is None:
        return []

    with psycopg.connect(DATABASE_URL) as conn:
        match = conn.execute(
            """select created_at from receipts
               where lower(merchant) = lower(%s) and purchase_date = %s and total = %s
               order by created_at limit 1""",
            (receipt.merchant, receipt.purchase_date, receipt.total),
        ).fetchone()

    if match is None:
        return []
    return [f"Possible duplicate: a receipt with the same store, date and total was saved on {match[0]:%b %d, %Y}."]


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
