create table if not exists public.form_submissions (
  id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('contact', 'booking')),
  reference text unique,
  name text not null,
  email text not null,
  practice text,
  message text,
  specialty text,
  providers text,
  preferred_date date,
  preferred_time text,
  submission_key text not null unique,
  notification_status text not null default 'pending' check (notification_status in ('pending', 'sent', 'failed')),
  notification_error text,
  visitor_confirmation_status text not null default 'pending' check (visitor_confirmation_status in ('pending', 'sent', 'failed', 'disabled')),
  visitor_confirmation_error text,
  created_at timestamptz not null default now()
);

create index if not exists form_submissions_email_created_at_idx
  on public.form_submissions (email, created_at desc);

create index if not exists form_submissions_kind_created_at_idx
  on public.form_submissions (kind, created_at desc);

alter table public.form_submissions enable row level security;

create policy "Service role can read submissions"
  on public.form_submissions
  for select
  to service_role
  using (true);

-- Walkthrough requests are stored separately from contact/booking submissions.
-- The row is written before any email is attempted so a Resend outage cannot
-- lose a request. `status` tracks the request lifecycle (awaiting team
-- confirmation by default); `notification_status` tracks email delivery.
create table if not exists public.walkthrough_submissions (
  id uuid primary key default gen_random_uuid(),
  reference text unique,
  first_name text not null,
  last_name text not null,
  email text not null,
  practice text not null,
  specialty text not null,
  providers text not null,
  preferred_date date not null,
  preferred_time text,
  submission_key text not null unique,
  status text not null default 'pending' check (status in ('pending', 'confirmed', 'cancelled')),
  notification_status text not null default 'pending' check (notification_status in ('pending', 'sent', 'failed')),
  notification_error text,
  notification_id text,
  created_at timestamptz not null default now()
);

create index if not exists walkthrough_submissions_email_created_at_idx
  on public.walkthrough_submissions (email, created_at desc);

create index if not exists walkthrough_submissions_status_created_at_idx
  on public.walkthrough_submissions (status, created_at desc);

alter table public.walkthrough_submissions enable row level security;

create policy "Service role can read walkthrough submissions"
  on public.walkthrough_submissions
  for select
  to service_role
  using (true);