from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from schemas import Receipt, ReceiptResult


def receipt(**overrides) -> Receipt:
    # Numbers, not strings, because that's what the model sends
    values = {
        "merchant": "DOLLAR TREE",
        "purchase_date": "2024-09-19",
        "items": [{"raw_text": "RING POP", "item_code": None, "quantity": 1, "unit_price": None, "line_total": 1.25}],
        "subtotal": 1.25,
        "tax": 0,
        "tip": None,
        "total": 1.25,
    }
    return Receipt(**(values | overrides))


def test_money_from_the_model_has_no_float_error():
    # Decimal(0.1) is 0.1000000000000000055..., so this checks the conversion keeps the printed digits
    assert receipt(total=0.1).total == Decimal("0.1")


def test_printed_time_is_dropped_from_the_date():
    assert receipt(purchase_date="2024-09-19T14:32:07").purchase_date == date(2024, 9, 19)


@pytest.mark.parametrize("printed", ["2024-02-30", "09/19/2024", "SEPT 19"])
def test_unusable_date_becomes_null_instead_of_failing_the_receipt(printed):
    # Null gets flagged for review, while a validation error would throw away every line item
    assert receipt(purchase_date=printed).purchase_date is None


def test_money_leaves_the_api_as_exact_strings():
    data = ReceiptResult(id=uuid4(), receipt=receipt(), issues=[]).model_dump(mode="json")
    assert data["receipt"]["total"] == "1.25"
    assert data["receipt"]["items"][0]["line_total"] == "1.25"
