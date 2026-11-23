-- Dedicated walkthrough request submissions.
-- Stored before any email attempt so a Resend outage cannot lose a request.
-- `status` is the request lifecycle (pending = awaiting team confirmation).
-- `notification_status` tracks email delivery and `notification_id` stores the
-- Resend delivery reference when available.

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

drop policy if exists "Service role can read walkthrough submissions" on public.walkthrough_submissions;

create policy "Service role can read walkthrough submissions"
  on public.walkthrough_submissions
  for select
  to service_role
  using (true);

notify pgrst, 'reload schema';