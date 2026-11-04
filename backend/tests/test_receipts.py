import base64

import pytest
from langchain_core.exceptions import OutputParserException
from langchain_google_genai.chat_models import GoogleAPIError

from receipts import PROMPT, extract_receipt
from schemas import Receipt


class FakeExtractor:
    """Stands in for the Gemini extractor: records what it was sent and returns a canned result."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.result


def test_sends_the_prompt_and_the_image():
    fake = FakeExtractor()
    extract_receipt(b"photo bytes", "image/png", fake)

    [message] = fake.messages
    assert message["role"] == "user"
    assert message["content"] == [
        {"type": "text", "text": PROMPT},
        {"type": "image", "base64": base64.b64encode(b"photo bytes").decode(), "mime_type": "image/png"},
    ]


def test_returns_the_parsed_receipt():
    receipt = Receipt(merchant="DOLLAR TREE", purchase_date=None, items=[], subtotal=None, tax=None, tip=None, total=None)
    assert extract_receipt(b"photo", "image/jpeg", FakeExtractor(result=receipt)) is receipt


def test_output_that_does_not_fit_the_schema_counts_as_unreadable():
    # Reached only after the fallback model also failed, so the endpoint can say "try a clearer photo"
    fake = FakeExtractor(error=OutputParserException("Failed to parse Receipt"))
    assert extract_receipt(b"photo", "image/jpeg", fake) is None


def test_model_outage_is_not_mistaken_for_an_unreadable_photo():
    # An outage must reach the endpoint as an error, so it says "try again in a minute" instead
    fake = FakeExtractor(error=GoogleAPIError(503, {"error": {"message": "overloaded"}}))
    with pytest.raises(GoogleAPIError):
        extract_receipt(b"photo", "image/jpeg", fake)
