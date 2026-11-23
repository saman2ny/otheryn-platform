import test from 'node:test';
import assert from 'node:assert/strict';
import { walkthroughSchema, type WalkthroughInput } from '../../src/lib/validation';
import { submitWalkthrough } from './walkthroughSubmission';

const futureDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
const pastDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

const data: WalkthroughInput = {
  firstName: 'Amina',
  lastName: 'Rahman',
  email: 'amina@example.com',
  practice: 'Test Practice',
  specialty: 'Dental',
  providers: '2–5 providers',
  date: futureDate,
  time: '09:00',
};

type InsertResult = {
  data: { id: string } | null;
  error: { code?: string; message?: string } | null;
};

const createSupabase = (options: {
  insertResult: InsertResult;
  existing?: { id: string; reference?: string | null; notification_status?: string | null } | null;
}) => {
  const calls = {
    events: [] as string[],
    inserts: [] as Array<{ table: string; values: Record<string, unknown> }>,
    updates: [] as Array<{
      values: Record<string, unknown>;
      eq: Array<{ column: string; value: unknown }>;
    }>,
    lookups: [] as Array<{ table: string; columns: string }>,
  };

  const supabase = {
    from(table: string) {
      return {
        insert(values: Record<string, unknown>) {
          calls.events.push('insert');
          calls.inserts.push({ table, values });
          return {
            select() {
              return {
                single: async () => options.insertResult,
              };
            },
          };
        },
        select(columns: string) {
          calls.lookups.push({ table, columns });
          return {
            eq() {
              return {
                single: async () => ({
                  data: options.existing ?? null,
                  error: null,
                }),
              };
            },
          };
        },
        update(values: Record<string, unknown>) {
          calls.events.push('update');
          const entry = { values, eq: [] as Array<{ column: string; value: unknown }> };
          calls.updates.push(entry);
          return {
            eq: async (column: string, value: unknown) => {
              entry.eq.push({ column, value });
              return { error: null };
            },
          };
        },
      };
    },
  };

  return { supabase, calls };
};

type SendNotification = (
  data: WalkthroughInput & { reference: string },
) => Promise<string | undefined>;

const params = (overrides: {
  supabase: ReturnType<typeof createSupabase>['supabase'];
  sendNotification: SendNotification;
  submissionKey?: string;
}) => ({
  data,
  submissionKey: overrides.submissionKey ?? 'walkthrough-key',
  reference: 'OY-TEST01',
  supabase: overrides.supabase as never,
  sendNotification: overrides.sendNotification,
});

test('walkthrough schema accepts a valid request', () => {
  const result = walkthroughSchema.safeParse(data);

  assert.equal(result.success, true);
});

test('walkthrough schema rejects an invalid email', () => {
  const result = walkthroughSchema.safeParse({ ...data, email: 'not-an-email' });

  assert.equal(result.success, false);
  if (!result.success) {
    assert.ok(result.error.issues.some((issue) => issue.path[0] === 'email'));
  }
});

test('walkthrough schema reports missing required fields', () => {
  const result = walkthroughSchema.safeParse({ date: futureDate });

  assert.equal(result.success, false);
  if (!result.success) {
    const fields = new Set(result.error.issues.map((issue) => String(issue.path[0])));
    for (const field of [
      'firstName',
      'lastName',
      'email',
      'practice',
      'specialty',
      'providers',
      'time',
    ]) {
      assert.ok(fields.has(field), `expected an error for ${field}`);
    }
  }
});

test('walkthrough schema rejects a past preferred date', () => {
  const result = walkthroughSchema.safeParse({ ...data, date: pastDate });

  assert.equal(result.success, false);
  if (!result.success) {
    assert.ok(result.error.issues.some((issue) => issue.path[0] === 'date'));
  }
});

test('walkthrough schema rejects a malformed preferred date', () => {
  const result = walkthroughSchema.safeParse({ ...data, date: '2999-13-40' });

  assert.equal(result.success, false);
});

test('walkthrough schema rejects an unsupported provider count', () => {
  const result = walkthroughSchema.safeParse({ ...data, providers: '999 providers' });

  assert.equal(result.success, false);
  if (!result.success) {
    assert.ok(result.error.issues.some((issue) => issue.path[0] === 'providers'));
  }
});

test('walkthrough saves the request before attempting email delivery', async () => {
  const { supabase, calls } = createSupabase({
    insertResult: { data: { id: 'row-1' }, error: null },
  });

  const result = await submitWalkthrough(
    params({
      supabase,
      sendNotification: async () => {
        calls.events.push('email');
        return 'email-123';
      },
    }),
  );

  assert.equal(calls.events[0], 'insert');
  assert.equal(calls.events[1], 'email');

  assert.equal(calls.inserts.length, 1);
  assert.equal(calls.inserts[0].values.status, 'pending');
  assert.equal(calls.inserts[0].values.notification_status, 'pending');
  assert.equal(calls.inserts[0].values.first_name, data.firstName);
  assert.equal(calls.inserts[0].values.preferred_date, data.date);

  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.reference, 'OY-TEST01');
  assert.equal(result.body.notificationStatus, 'sent');

  assert.equal(calls.updates.length, 1);
  assert.equal(calls.updates[0].values.notification_status, 'sent');
  assert.equal(calls.updates[0].values.notification_id, 'email-123');
});

test('walkthrough returns 500 when the database insert fails', async () => {
  const { supabase, calls } = createSupabase({
    insertResult: { data: null, error: { message: 'Database unavailable' } },
  });

  const result = await submitWalkthrough(
    params({ supabase, sendNotification: async () => 'email-1' }),
  );

  assert.equal(result.status, 500);
  assert.equal(result.body.ok, false);
  assert.match(String(result.body.error), /Unable to save/);
  assert.equal(calls.updates.length, 0);
});

test('walkthrough keeps the saved request when email delivery fails', async () => {
  const { supabase, calls } = createSupabase({
    insertResult: { data: { id: 'row-2' }, error: null },
  });

  const result = await submitWalkthrough(
    params({
      supabase,
      sendNotification: async () => {
        throw new Error('Resend unavailable');
      },
    }),
  );

  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.saved, true);
  assert.equal(result.body.notificationStatus, 'failed');

  assert.equal(calls.inserts.length, 1);
  assert.equal(calls.updates.length, 1);
  assert.equal(calls.updates[0].values.notification_status, 'failed');
});

test('walkthrough rejects a duplicate submission', async () => {
  const { supabase } = createSupabase({
    insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
    existing: { id: 'row-3', reference: 'OY-OLD01', notification_status: 'sent' },
  });

  const result = await submitWalkthrough(
    params({ supabase, sendNotification: async () => 'email-3' }),
  );

  assert.equal(result.status, 409);
  assert.equal(result.body.ok, false);
  assert.match(String(result.body.error), /already received/);
});

test('walkthrough retries email for a duplicate whose notification previously failed', async () => {
  const { supabase, calls } = createSupabase({
    insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
    existing: { id: 'row-4', reference: 'OY-OLD02', notification_status: 'failed' },
  });

  const result = await submitWalkthrough(
    params({ supabase, sendNotification: async () => 'email-retry' }),
  );

  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.retried, true);
  assert.equal(result.body.notificationStatus, 'sent');
  assert.equal(calls.updates.length, 1);
  assert.equal(calls.updates[0].values.notification_status, 'sent');
});

test('walkthrough reports a missing table clearly', async () => {
  const { supabase } = createSupabase({
    insertResult: {
      data: null,
      error: { message: 'Could not find the table public.walkthrough_submissions' },
    },
  });

  const result = await submitWalkthrough(
    params({ supabase, sendNotification: async () => 'email-5' }),
  );

  assert.equal(result.status, 500);
  assert.match(String(result.body.error), /walkthrough_submissions table is missing/);
});

test('walkthrough duplicate lookup failure is handled safely', async () => {
  const supabase = {
    from() {
      return {
        insert() {
          return {
            select() {
              return {
                single: async () => ({
                  data: null,
                  error: { code: '23505', message: 'duplicate key value' },
                }),
              };
            },
          };
        },
        select() {
          return {
            eq() {
              return {
                single: async () => {
                  throw new Error('lookup failed');
                },
              };
            },
          };
        },
      };
    },
  };

  const result = await submitWalkthrough(
    params({ supabase: supabase as never, sendNotification: async () => 'email-6' }),
  );

  assert.equal(result.status, 500);
  assert.equal(result.body.ok, false);
});