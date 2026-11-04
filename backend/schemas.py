from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

class Link(BaseModel):
    """A page the treasurer can act on"""
    label: str = Field(description="What the page is for, e.g. 'Panda Express fundraiser sign-up'")
    url: str = Field(description="URL returned by a tool")

class Answer(BaseModel):
    """A researched answer to the treasurer's question"""
    summary: str = Field(description="The answer to the treasurer's question, based on the sources")
    action_links: list[Link] = Field(description="Pages where the treasurer can take the next step: sign-up or registration forms, applications, order pages. Only URLs returned by tools. Empty list if none")
    sources: list[str] = Field(description="URLs returned by tools that support the answer. Empty list if no tool returned a URL")

class ChatRequest(BaseModel):
    message: str

class LineItem(BaseModel):
    """One line on a receipt"""
    raw_text: str = Field(description="The item name exactly as printed, without its code or price, e.g. 'GV WHL MLK'")
    item_code: str | None = Field(description="The printed product or UPC code. Null if none is printed")
    quantity: Decimal = Field(description="The printed quantity or weight, 1 if none is printed")
    unit_price: Decimal | None = Field(description="The printed price per unit or per pound. Null if none is printed")
    line_total: Decimal = Field(description="The amount printed for this line. Negative for discounts and coupons")

# Fields are nullable because a required field pressures the model to invent a value
class Receipt(BaseModel):
    """The values printed on one receipt. Null means missing or unreadable, never a guess"""
    merchant: str | None = Field(description="The store or restaurant name. Null if unreadable")
    purchase_date: date | None = Field(description="The purchase date as YYYY-MM-DD. Null if unreadable")
    items: list[LineItem] = Field(description="Every item, fee, deposit and discount in printed order. Leave out subtotal, tax, tip, total and payment lines")
    subtotal: Decimal | None = Field(description="The printed subtotal. Null if none is printed")
    tax: Decimal | None = Field(description="The printed tax. Null if none is printed")
    tip: Decimal | None = Field(description="The tip, including a handwritten one. Null if none")
    total: Decimal | None = Field(description="The final amount paid, including a handwritten total. Null if unreadable")

    @field_validator("purchase_date", mode="before")
    @classmethod
    def parse_printed_date(cls, value):
        # The model sometimes copies the time too, which a date field rejects. A date that still
        # won't parse (misread as 2026-02-30, say) becomes null and gets flagged, instead of
        # failing validation and losing every line item with it
        if not isinstance(value, str):
            return value
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

class ReceiptResult(BaseModel):
    id: UUID
    receipt: Receipt
    issues: list[str]

class ReceiptDetail(ReceiptResult):
    status: str
    created_at: datetime
    image_url: str = Field(description="A link to the photo that expires after a few minutes")

class ReceiptSummary(BaseModel):
    id: UUID
    merchant: str | None
    purchase_date: date | None
    total: Decimal | None
    status: str
    issues: list[str]
    created_at: datetime