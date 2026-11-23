import test from 'node:test';
import assert from 'node:assert/strict';
import type { ContactInput } from '../../src/lib/validation';
import { submitContactEmailFirst } from './contactSubmission';

const data: ContactInput = {
  name: 'Amina Rahman',
  email: 'amina@example.com',
  practice: 'Test Practice',
  message: 'Automated contact submission test.',
};

const createSupabase = (insertResult: {
  data: { id: string } | null;
  error: { message?: string } | null;
}) => {
  const calls = {
    inserts: [] as Array<{ table: string; values: Record<string, unknown> }>,
    updates: [] as Array<{
      values: Record<string, unknown>;
      eq: Array<{ column: string; value: unknown }>;
    }>,
  };

  const supabase = {
    from(table: string) {
      return {
        insert(values: Record<string, unknown>) {
          calls.inserts.push({ table, values });
          return {
            select() {
              return {
                single: async () => insertResult,
              };
            },
          };
        },
        update(values: Record<string, unknown>) {
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

const params = (overrides: {
  supabase: ReturnType<typeof createSupabase>['supabase'];
  sendNotification: (data: ContactInput) => Promise<string | undefined>;
  submissionKey?: string;
  visitorConfirmationEnabled?: boolean;
  sendVisitorConfirmation?: (data: {
    kind: 'contact';
    email: string;
    name: string;
    reference: string;
  }) => Promise<unknown>;
}) => ({
  data,
  submissionKey: overrides.submissionKey ?? 'contact-key',
  supabase: overrides.supabase as never,
  sendNotification: overrides.sendNotification,
  sendVisitorConfirmation: overrides.sendVisitorConfirmation ?? (async () => undefined),
  visitorConfirmationEnabled: overrides.visitorConfirmationEnabled ?? false,
});

test('contact email-first does not insert when Resend rejects', async () => {
  const { supabase, calls } = createSupabase({ data: { id: 'row-1' }, error: null });
  const result = await submitContactEmailFirst(
    params({
      supabase,
      submissionKey: 'reject-key',
      sendNotification: async () => {
        throw new Error(
          'You can only send testing emails to your own email address (hello.otheryn@gmail.com).',
        );
      },
    }),
  );

  assert.equal(result.status, 502);
  assert.equal(calls.inserts.length, 0);
  assert.match(String(result.body.error), /Resend test mode/);
});

test('contact email-first saves the enquiry after Resend acceptance', async () => {
  const { supabase, calls } = createSupabase({ data: { id: 'row-1' }, error: null });
  const result = await submitContactEmailFirst(
    params({
      supabase,
      submissionKey: 'accept-key',
      sendNotification: async () => 'email-123',
    }),
  );

  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.reference, 'row-1');
  assert.equal(result.body.notificationId, 'email-123');
  assert.equal(calls.inserts.length, 1);
  assert.equal(calls.inserts[0].values.notification_status, 'sent');
});

test('contact email-first reports partial failure when Supabase insert fails', async () => {
  const { supabase, calls } = createSupabase({
    data: null,
    error: { message: 'Database unavailable' },
  });
  const result = await submitContactEmailFirst(
    params({
      supabase,
      submissionKey: 'insert-fail-key',
      sendNotification: async () => 'email-123',
    }),
  );

  assert.equal(result.status, 500);
  assert.equal(result.body.ok, false);
  assert.equal(result.body.partialFailure, true);
  assert.equal(result.body.notificationId, 'email-123');
  assert.match(String(result.body.error), /could not be saved/);
  assert.equal(calls.inserts.length, 1);
});

test('contact email-first returns success with visitor confirmation', async () => {
  const { supabase, calls } = createSupabase({ data: { id: 'row-2' }, error: null });
  const result = await submitContactEmailFirst(
    params({
      supabase,
      submissionKey: 'success-key',
      sendNotification: async () => 'email-456',
      visitorConfirmationEnabled: true,
      sendVisitorConfirmation: async () => 'confirmation-1',
    }),
  );

  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.reference, 'row-2');
  assert.equal(result.body.notificationId, 'email-456');
  assert.equal(calls.updates.length, 1);
  assert.equal(calls.updates[0].values.visitor_confirmation_status, 'sent');
});

test('contact email-first prevents duplicate insertion on double-click', async () => {
  const { supabase, calls } = createSupabase({ data: { id: 'row-3' }, error: null });
  const request = params({
    supabase,
    submissionKey: 'double-key',
    sendNotification: async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
      return 'email-double';
    },
  });

  const first = submitContactEmailFirst(request);
  const second = await submitContactEmailFirst(request);
  const firstResult = await first;

  assert.equal(calls.inserts.length, 1);
  assert.equal(second.status, 409);
  assert.equal(firstResult.status, 200);
});