from decimal import Decimal

from schemas import Receipt

# Priced-by-weight lines round to the cent, so quantity x price can differ by a fraction of one
LINE_TOLERANCE = Decimal("0.01")


def check_receipt(receipt: Receipt) -> list[str]:
    """Return each reason a person should review this receipt. An empty list means every check passed.

    The model reads the numbers and this code does the math, so a misread digit gets caught
    instead of trusted. Nothing here calls the model, so the checks run without an API key."""
    issues = []

    if not receipt.merchant:
        issues.append("Couldn't read the store name.")
    if receipt.purchase_date is None:
        issues.append("Couldn't read the purchase date.")
    if not receipt.items:
        issues.append("No line items found.")

    for item in receipt.items:
        if item.unit_price is not None:
            expected = item.quantity * item.unit_price
            if abs(expected - item.line_total) > LINE_TOLERANCE:
                issues.append(f"{item.raw_text}: {item.quantity} x {item.unit_price} is {expected}, but the line says {item.line_total}.")

    items_sum = sum((item.line_total for item in receipt.items), Decimal(0))
    subtotal = items_sum if receipt.subtotal is None else receipt.subtotal
    if subtotal != items_sum:
        issues.append(f"Line items add up to {items_sum}, but the subtotal says {subtotal}.")

    if receipt.total is None:
        issues.append("Couldn't read the total.")
    else:
        # Tax is often absent (Delaware has no sales tax), so a missing tax isn't an issue by itself
        expected_total = subtotal + (receipt.tax or 0) + (receipt.tip or 0)
        if expected_total != receipt.total:
            issues.append(f"Subtotal, tax and tip add up to {expected_total}, but the total says {receipt.total}.")

    return issues
