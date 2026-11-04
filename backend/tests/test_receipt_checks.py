import pytest

from receipt_checks import check_receipt
from schemas import LineItem, Receipt


def item(line_total: str, quantity: str = "1", unit_price: str | None = None) -> LineItem:
    return LineItem(raw_text="ITEM", item_code=None, quantity=quantity, unit_price=unit_price, line_total=line_total)


def receipt(**overrides) -> Receipt:
    values = {
        "merchant": "CAMPUS MART",
        "purchase_date": "2026-09-14",
        "items": [item("3.62"), item("2.98")],
        "subtotal": "6.60",
        "tax": "0.40",
        "tip": None,
        "total": "7.00",
    }
    return Receipt(**(values | overrides))


def test_clean_receipt_has_no_issues():
    assert check_receipt(receipt()) == []


def test_money_math_is_exact():
    # These add up as Decimals, but 0.1 + 0.2 != 0.3 as floats
    assert check_receipt(receipt(items=[item("0.10"), item("0.20")], subtotal="0.30", tax=None, total="0.30")) == []


def test_subtotal_mismatch_is_flagged():
    issues = check_receipt(receipt(subtotal="6.70", total="7.10"))
    assert issues == ["Line items add up to 6.60, but the subtotal says 6.70."]


def test_total_mismatch_is_flagged():
    issues = check_receipt(receipt(total="7.10"))
    assert issues == ["Subtotal, tax and tip add up to 7.00, but the total says 7.10."]


def test_missing_subtotal_falls_back_to_the_item_sum():
    assert check_receipt(receipt(subtotal=None)) == []


def test_no_sales_tax_is_not_an_issue():
    assert check_receipt(receipt(tax=None, total="6.60")) == []


def test_tip_counts_toward_the_total():
    assert check_receipt(receipt(tax=None, tip="1.40", total="8.00")) == []


def test_discount_lines_reduce_the_sum():
    assert check_receipt(receipt(items=[item("7.60"), item("-1.00")])) == []


def test_quantity_times_price_is_checked():
    issues = check_receipt(receipt(items=[item("3.00", "2", "1.60"), item("3.60")]))
    assert issues == ["ITEM: 2 x 1.60 is 3.20, but the line says 3.00."]


def test_priced_by_weight_rounding_is_allowed():
    # 1.32 x 2.99 = 3.9468, printed as 3.95
    assert check_receipt(receipt(items=[item("3.95", "1.32", "2.99"), item("2.65")])) == []


@pytest.mark.parametrize("missing, message", [
    ({"merchant": None}, "Couldn't read the store name."),
    ({"purchase_date": None}, "Couldn't read the purchase date."),
    ({"total": None}, "Couldn't read the total."),
])
def test_unreadable_fields_are_flagged(missing, message):
    assert check_receipt(receipt(**missing)) == [message]


def test_no_items_is_flagged():
    issues = check_receipt(receipt(items=[], subtotal=None, tax=None, total="0"))
    assert issues == ["No line items found."]
