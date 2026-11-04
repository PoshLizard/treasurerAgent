// Shapes of the backend's JSON. Amounts arrive as strings so no cents are lost to float rounding.
export type LineItem = {
  raw_text: string;
  item_code: string | null;
  quantity: string;
  unit_price: string | null;
  line_total: string;
};
export type Receipt = {
  merchant: string | null;
  purchase_date: string | null;
  items: LineItem[];
  subtotal: string | null;
  tax: string | null;
  tip: string | null;
  total: string | null;
};
export type ReceiptResult = { id: string; receipt: Receipt; issues: string[] };
export type ReceiptDetail = ReceiptResult & { status: string; created_at: string; image_url: string };
export type ReceiptSummary = {
  id: string;
  merchant: string | null;
  purchase_date: string | null;
  total: string | null;
  status: string;
  issues: string[];
  created_at: string;
};

const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
export const formatMoney = (amount: string | null) => (amount === null ? "Not shown" : dollars.format(Number(amount)));

// "2024-09-19" parses as midnight UTC, so format it in UTC too. In local time, anyone west of
// London would see the day before.
const dates = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" });
export const formatDate = (isoDate: string | null) => (isoDate === null ? "Unknown date" : dates.format(new Date(isoDate)));

export const STATUS_LABELS: Record<string, string> = { needs_review: "Needs review", approved: "Approved" };
