"""The eval is only useful if it scores correctly, so its scoring gets tests too."""
import pytest

from run_receipts import classify, wrong_fields
from schemas import Receipt


def receipt(**overrides) -> Receipt:
    values = {
        "merchant": "Dollar Tree",
        "purchase_date": "2024-09-19",
        "items": [
            {"raw_text": "RING POP", "item_code": None, "quantity": "1", "unit_price": None, "line_total": "1.25"},
            {"raw_text": "PLUSH CAT HEADBAND", "item_code": None, "quantity": "1", "unit_price": None, "line_total": "1.75"},
        ],
        "subtotal": "3.00",
        "tax": "0",
        "tip": None,
        "total": "3.00",
    }
    return Receipt(**(values | overrides))


def test_matching_receipt_has_no_wrong_fields():
    assert wrong_fields(receipt(), receipt()) == []


def test_merchant_capitalization_is_ignored():
    assert wrong_fields(receipt(), receipt(merchant="DOLLAR TREE")) == []


def test_item_order_is_ignored():
    expected = receipt()
    assert wrong_fields(expected, receipt(items=list(reversed(expected.items)))) == []


def test_each_wrong_field_is_named():
    actual = receipt(total="3.50", items=receipt().items[:1])
    assert wrong_fields(receipt(), actual) == ["total", "items"]


@pytest.mark.parametrize("wrong, flagged, outcome", [
    ([], False, "correct"),
    ([], True, "correct, flagged"),
    (["total"], True, "wrong, flagged"),
    (["total"], False, "SILENT ERROR"),
])
def test_outcomes(wrong, flagged, outcome):
    assert classify(wrong, flagged) == outcome
