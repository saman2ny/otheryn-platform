import './loadEnv';
import test from 'node:test';
import assert from 'node:assert/strict';
import { supabase, supabaseConfigured } from './supabase';

test('Supabase increment_rate_limit RPC matches the deployed function', async () => {
  if (!supabaseConfigured || !supabase) {
    console.log('Skipping Supabase RPC integration test: Supabase is not configured.');
    return;
  }

  const client = supabase;
  const bucketKey = `integration:${Date.now()}`;
  const { data, error } = await client.rpc('increment_rate_limit', {
    p_bucket_key: bucketKey,
    p_window_seconds: 60,
    p_max_requests: 1,
  });

  if (error) {
    assert.notEqual(error.code, '42702', 'ambiguous_column regression');
    assert.fail(
      `RPC failed: code=${error.code} message=${error.message} details=${error.details ?? ''}`,
    );
  }

  const row = (Array.isArray(data) ? data[0] : data) as
    | { allowed?: unknown; request_count?: unknown; retry_after?: unknown }
    | undefined;

  assert.equal(typeof row?.allowed, 'boolean');
  assert.equal(typeof row?.request_count, 'number');
  assert.equal(typeof row?.retry_after, 'number');
});