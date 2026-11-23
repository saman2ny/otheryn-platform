import type { WalkthroughInput } from '../../src/lib/validation';
import { serializeEmailError } from './email';

type WalkthroughNotificationData = WalkthroughInput & { reference: string };

type InsertResult = {
  data: { id: string } | null;
  error: { code?: string; message?: string } | null;
};

type LookupResult = {
  data: { id: string; reference?: string | null; notification_status?: string | null } | null;
  error: { code?: string; message?: string } | null;
};

type SupabaseLike = {
  from: (table: 'walkthrough_submissions') => {
    insert: (values: Record<string, unknown>) => {
      select: (columns: string) => {
        single: () => Promise<InsertResult>;
      };
    };
    select: (columns: string) => {
      eq: (column: string, value: unknown) => {
        single: () => Promise<LookupResult>;
      };
    };
    update: (values: Record<string, unknown>) => {
      eq: (column: string, value: unknown) => Promise<{ error: unknown }>;
    };
  };
};

export type WalkthroughSubmissionResult = {
  status: number;
  body: Record<string, unknown>;
};

type WalkthroughSubmissionParams = {
  data: WalkthroughInput;
  submissionKey: string;
  reference: string;
  supabase: SupabaseLike;
  sendNotification: (data: WalkthroughNotificationData) => Promise<string | undefined>;
};

type DuplicateParams = Omit<WalkthroughSubmissionParams, 'submissionKey'> & {
  submissionKey: string;
};

const missingTableMessage =
  'The walkthrough_submissions table is missing. Apply supabase/schema.sql.';

const duplicateMessage = 'A walkthrough request with these details was already received.';

const saveFailedMessage = 'Unable to save your walkthrough request.';

export async function submitWalkthrough({
  data,
  submissionKey,
  reference,
  supabase,
  sendNotification,
}: WalkthroughSubmissionParams): Promise<WalkthroughSubmissionResult> {
  let insertResult: InsertResult;

  try {
    insertResult = await supabase
      .from('walkthrough_submissions')
      .insert({
        reference,
        first_name: data.firstName,
        last_name: data.lastName,
        email: data.email,
        practice: data.practice,
        specialty: data.specialty,
        providers: data.providers,
        preferred_date: data.date,
        preferred_time: data.time,
        submission_key: submissionKey,
        status: 'pending',
        notification_status: 'pending',
      })
      .select('id')
      .single();
  } catch (error) {
    console.error('Supabase walkthrough insert threw', error);
    return { status: 500, body: { ok: false, error: saveFailedMessage } };
  }

  const { data: row, error } = insertResult;

  if (error || !row) {
    if (error?.code === '23505') {
      return handleDuplicate({ data, submissionKey, reference, supabase, sendNotification });
    }

    console.error('Supabase walkthrough insert failed', error);
    const missingTable = error?.message?.includes('Could not find the table');
    return {
      status: 500,
      body: {
        ok: false,
        error: missingTable ? missingTableMessage : saveFailedMessage,
      },
    };
  }

  const id = String(row.id);

  try {
    const notificationId = await sendNotification({ ...data, reference });

    await supabase
      .from('walkthrough_submissions')
      .update({
        notification_status: 'sent',
        notification_id: notificationId ?? null,
        notification_error: null,
      })
      .eq('id', id);

    return {
      status: 200,
      body: {
        ok: true,
        id,
        reference,
        notificationStatus: 'sent',
        ...(notificationId ? { notificationId } : {}),
      },
    };
  } catch (emailError) {
    const details = serializeEmailError(emailError);
    console.error('Walkthrough notification failed', details);

    try {
      await supabase
        .from('walkthrough_submissions')
        .update({
          notification_status: 'failed',
          notification_error: details,
        })
        .eq('id', id);
    } catch (updateError) {
      console.error('Failed to mark walkthrough notification as failed', updateError);
    }

    // The request was persisted before the email attempt, so this is not a user-facing failure.
    return {
      status: 200,
      body: {
        ok: true,
        id,
        reference,
        saved: true,
        notificationStatus: 'failed',
      },
    };
  }
}

async function handleDuplicate({
  data,
  submissionKey,
  reference,
  supabase,
  sendNotification,
}: DuplicateParams): Promise<WalkthroughSubmissionResult> {
  let lookup: LookupResult;

  try {
    lookup = await supabase
      .from('walkthrough_submissions')
      .select('id, reference, notification_status')
      .eq('submission_key', submissionKey)
      .single();
  } catch (error) {
    console.error('Supabase walkthrough duplicate lookup threw', error);
    return { status: 500, body: { ok: false, error: saveFailedMessage } };
  }

  const existing = lookup.data;

  if (!existing || existing.notification_status !== 'failed') {
    return { status: 409, body: { ok: false, error: duplicateMessage } };
  }

  const existingReference = String(existing.reference ?? reference);

  try {
    const notificationId = await sendNotification({ ...data, reference: existingReference });

    await supabase
      .from('walkthrough_submissions')
      .update({
        notification_status: 'sent',
        notification_id: notificationId ?? null,
        notification_error: null,
      })
      .eq('id', existing.id);

    return {
      status: 200,
      body: {
        ok: true,
        id: existing.id,
        reference: existingReference,
        retried: true,
        notificationStatus: 'sent',
        ...(notificationId ? { notificationId } : {}),
      },
    };
  } catch (emailError) {
    const details = serializeEmailError(emailError);
    console.error('Walkthrough notification retry failed', details);

    try {
      await supabase
        .from('walkthrough_submissions')
        .update({ notification_status: 'failed', notification_error: details })
        .eq('id', existing.id);
    } catch (updateError) {
      console.error('Failed to mark walkthrough retry as failed', updateError);
    }

    return {
      status: 200,
      body: {
        ok: true,
        id: existing.id,
        reference: existingReference,
        retried: true,
        saved: true,
        notificationStatus: 'failed',
      },
    };
  }
}