-- Database tables. To set up a new environment, run this in the Supabase SQL Editor.
-- Safe to run more than once.

create table if not exists receipts (
    id uuid primary key,
    merchant text,
    purchase_date date,
    subtotal numeric,
    tax numeric,
    tip numeric,
    total numeric,
    issues text[] not null default '{}',
    status text not null default 'needs_review' check (status in ('needs_review', 'approved')),
    image_path text not null,
    created_at timestamptz not null default now()
);

create table if not exists line_items (
    id uuid primary key default gen_random_uuid(),
    receipt_id uuid not null references receipts (id) on delete cascade,
    position integer not null,
    raw_text text not null,
    item_code text,
    quantity numeric not null,
    unit_price numeric,
    line_total numeric not null,
    unique (receipt_id, position)
);

-- With no policies, row level security blocks everything arriving through Supabase's public APIs.
-- The backend connects as the table owner, which row level security doesn't apply to.
alter table receipts enable row level security;
alter table line_items enable row level security;
