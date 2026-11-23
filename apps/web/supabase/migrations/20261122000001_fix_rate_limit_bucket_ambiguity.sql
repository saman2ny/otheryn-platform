-- Fix ambiguous request_count reference inside the existing rate-limit function.

create or replace function public.increment_rate_limit(
  p_bucket_key text,
  p_window_seconds integer,
  p_max_requests integer
)
returns table (allowed boolean, request_count integer, retry_after integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_now timestamptz := now();
  v_window_start timestamptz := now() - make_interval(secs => p_window_seconds);
  v_row public.rate_limit_buckets%rowtype;
  v_count integer;
  v_retry_after integer;
begin
  update public.rate_limit_buckets as buckets
     set request_count = buckets.request_count + 1,
         updated_at = v_now
   where buckets.bucket_key = p_bucket_key
     and buckets.window_started_at > v_window_start
  returning * into v_row;

  if found then
    v_count := v_row.request_count;
    v_retry_after := greatest(
      0,
      ceil(extract(epoch from (v_row.window_started_at + make_interval(secs => p_window_seconds) - v_now)))::int
    );
    return query select v_count <= p_max_requests, v_count, v_retry_after;
    return;
  end if;

  insert into public.rate_limit_buckets as buckets (
    bucket_key,
    window_started_at,
    request_count,
    updated_at
  )
  values (p_bucket_key, v_now, 1, v_now)
  on conflict (bucket_key) do update
    set request_count = case
          when buckets.window_started_at > v_window_start then buckets.request_count + 1
          else 1
        end,
        window_started_at = case
          when buckets.window_started_at > v_window_start then buckets.window_started_at
          else v_now
        end,
        updated_at = v_now
  returning * into v_row;

  v_count := v_row.request_count;
  v_retry_after := greatest(
    0,
    ceil(extract(epoch from (v_row.window_started_at + make_interval(secs => p_window_seconds) - v_now)))::int
  );
  return query select v_count <= p_max_requests, v_count, v_retry_after;
end;
$$;

revoke all on function public.increment_rate_limit(text, integer, integer) from public;
revoke all on function public.increment_rate_limit(text, integer, integer) from anon;
revoke all on function public.increment_rate_limit(text, integer, integer) from authenticated;
grant execute on function public.increment_rate_limit(text, integer, integer) to service_role;

notify pgrst, 'reload schema';