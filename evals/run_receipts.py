"""Score receipt extraction against hand-labeled receipts.

Put each image in evals/receipts/ beside a .json label with the same name, in the shape of
schemas.Receipt (see evals/synthetic/ for examples). That folder is gitignored because real
receipts hold personal data and this repo is public.

    python evals/run_receipts.py                  # real receipts, every model
    python evals/run_receipts.py evals/synthetic  # fake samples
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from receipt_checks import check_receipt
from receipts import build_extractor, extract_receipt
from schemas import Receipt

MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
              ".heic": "image/heic", ".heif": "image/heif"}


def wrong_fields(expected: Receipt, actual: Receipt) -> list[str]:
    """Return the name of each field the model got wrong."""
    wrong = [field for field in ("purchase_date", "subtotal", "tax", "tip", "total")
             if getattr(expected, field) != getattr(actual, field)]
    if (expected.merchant or "").casefold() != (actual.merchant or "").casefold():
        wrong.append("merchant")
    if Counter(item.line_total for item in expected.items) != Counter(item.line_total for item in actual.items):
        wrong.append("items")
    return wrong


def classify(wrong: list[str], flagged: bool) -> str:
    # A silent error is the outcome that matters: a wrong value nothing warned the treasurer about
    return {(False, False): "correct", (False, True): "correct, flagged",
            (True, True): "wrong, flagged", (True, False): "SILENT ERROR"}[(bool(wrong), flagged)]


def run_model(model_name: str, labeled: list[tuple[Path, Receipt]]) -> None:
    extractor = build_extractor(model_name)
    outcomes = Counter()
    field_errors = Counter()

    print(f"\n{model_name}")
    for image_path, expected in labeled:
        try:
            actual = extract_receipt(image_path.read_bytes(), MIME_TYPES[image_path.suffix.lower()], extractor)
        except Exception as error:
            actual, detail = None, type(error).__name__
        else:
            detail = "no result"

        if actual is None:
            outcomes["failed"] += 1
            print(f"  {image_path.name}: FAILED ({detail})")
            continue

        wrong = wrong_fields(expected, actual)
        field_errors.update(wrong)
        outcome = classify(wrong, flagged=bool(check_receipt(actual)))
        outcomes[outcome] += 1
        print(f"  {image_path.name}: {outcome}" + (f" ({', '.join(wrong)})" if wrong else ""))

    print(f"  outcomes: {dict(outcomes)}")
    if field_errors:
        print(f"  wrong fields: {dict(field_errors)}")


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evals" / "receipts"
    labeled = [(path, Receipt.model_validate_json(path.with_suffix(".json").read_text()))
               for path in sorted(folder.iterdir())
               if path.suffix.lower() in MIME_TYPES and path.with_suffix(".json").exists()]
    if not labeled:
        sys.exit(f"No labeled receipts in {folder}")

    print(f"{len(labeled)} labeled receipts in {folder}")
    for model_name in MODELS:
        run_model(model_name, labeled)


if __name__ == "__main__":
    main()
