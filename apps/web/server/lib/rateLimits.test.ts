import test from 'node:test';
import assert from 'node:assert/strict';
import type { Request } from 'express';
import { createRateLimitMiddleware } from './rateLimits';

type RpcResult = {
  data: unknown;
  error: { message?: string } | null;
};

const createSupabase = (
  handler: (fn: string, args: Record<string, unknown>) => Promise<RpcResult>,
) => {
  const calls: Array<{ fn: string; args: Record<string, unknown> }> = [];

  return {
    calls,
    rpc: async (fn: string, args: Record<string, unknown>) => {
      calls.push({ fn, args });
      return handler(fn, args);
    },
  };
};

const createRequest = (ip = '127.0.0.1') =>
  ({ ip, socket: { remoteAddress: ip } }) as Request;

const createResponse = () => {
  const response = {
    statusCode: 200,
    body: undefined as unknown,
    headers: {} as Record<string, string>,
    status(code: number) {
      response.statusCode = code;
      return response;
    },
    json(body: unknown) {
      response.body = body;
      return response;
    },
    setHeader(name: string, value: string) {
      response.headers[name.toLowerCase()] = String(value);
    },
  };

  return response;
};

const config = { max: 3, windowSeconds: 60 };

test('rate limiter allows requests below the limit', async () => {
  const supabase = createSupabase(async () => ({
    data: [{ allowed: true, request_count: 1, retry_after: 0 }],
    error: null,
  }));
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  const response = createResponse();
  let nextCalled = false;

  await middleware(createRequest(), response as never, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, true);
  assert.equal(response.statusCode, 200);
  const bucketKey = supabase.calls[0].args.p_bucket_key as string;
  assert.ok(bucketKey.startsWith('contact:'));
});

test('rate limiter returns 429 with Retry-After above the limit', async () => {
  const supabase = createSupabase(async () => ({
    data: [{ allowed: false, request_count: 4, retry_after: 42 }],
    error: null,
  }));
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  const response = createResponse();
  let nextCalled = false;

  await middleware(createRequest(), response as never, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, false);
  assert.equal(response.statusCode, 429);
  assert.equal(response.headers['retry-after'], '42');
  assert.equal((response.body as { ok: boolean }).ok, false);
});

test('rate limiter returns 503 when the database operation fails', async () => {
  const supabase = createSupabase(async () => ({
    data: null,
    error: { message: 'Database unavailable' },
  }));
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  const response = createResponse();
  let nextCalled = false;

  await middleware(createRequest(), response as never, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, false);
  assert.equal(response.statusCode, 503);
  assert.equal((response.body as { ok: boolean }).ok, false);
});

test('rate limiter never falls back when Supabase is unavailable', async () => {
  const middleware = createRateLimitMiddleware('contact', {
    supabase: null,
    salt: 'test-salt',
    config,
  });

  const response = createResponse();
  let nextCalled = false;

  await middleware(createRequest(), response as never, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, false);
  assert.equal(response.statusCode, 503);
});

test('rate limiter handles concurrent requests without exceeding the limit', async () => {
  let count = 0;
  const supabase = createSupabase(async () => {
    count += 1;
    const allowed = count <= 3;
    return {
      data: [{ allowed, request_count: count, retry_after: allowed ? 0 : 60 }],
      error: null,
    };
  });
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  const results = await Promise.all(
    Array.from({ length: 5 }, async () => {
      const response = createResponse();
      await middleware(createRequest(), response as never, () => undefined);
      return response.statusCode;
    }),
  );

  assert.equal(results.filter((status) => status === 200).length, 3);
  assert.equal(results.filter((status) => status === 429).length, 2);
});

test('contact and booking policies use isolated buckets', async () => {
  const supabase = createSupabase(async () => ({
    data: [{ allowed: true, request_count: 1, retry_after: 0 }],
    error: null,
  }));

  const contact = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });
  const booking = createRateLimitMiddleware('booking', {
    supabase,
    salt: 'test-salt',
    config,
  });

  await contact(createRequest(), createResponse() as never, () => undefined);
  await booking(createRequest(), createResponse() as never, () => undefined);

  const [contactKey, bookingKey] = supabase.calls.map(
    (call) => call.args.p_bucket_key as string,
  );

  assert.ok(contactKey.startsWith('contact:'));
  assert.ok(bookingKey.startsWith('booking:'));
  assert.notEqual(contactKey, bookingKey);
});

test('rate limiter returns 503 for ambiguous_column RPC failures', async () => {
  const supabase = createSupabase(async () => ({
    data: null,
    error: {
      code: '42702',
      message: 'column reference "request_count" is ambiguous',
      details: 'It could refer to either a PL/pgSQL variable or a table column.',
    },
  }));
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  const response = createResponse();
  let nextCalled = false;

  await middleware(createRequest(), response as never, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, false);
  assert.equal(response.statusCode, 503);
  assert.equal((response.body as { ok: boolean }).ok, false);
});

test('rate limiter stores hashed client identifiers, not raw IP addresses', async () => {
  const supabase = createSupabase(async () => ({
    data: [{ allowed: true, request_count: 1, retry_after: 0 }],
    error: null,
  }));
  const middleware = createRateLimitMiddleware('contact', {
    supabase,
    salt: 'test-salt',
    config,
  });

  await middleware(createRequest('203.0.113.42'), createResponse() as never, () => undefined);

  const bucketKey = supabase.calls[0].args.p_bucket_key as string;
  assert.ok(!bucketKey.includes('203.0.113.42'));
  assert.match(bucketKey, /^contact:[a-f0-9]{64}$/);
});