import type { ContactInput } from '../../src/lib/validation';
import { serializeEmailError } from './email';

type SupabaseLike = {
  from: (table: 'form_submissions') => {
    insert: (values: Record<string, unknown>) => {
      select: (columns: string) => {
        single: () => Promise<{ data: { id: string } | null; error: { message?: string } | null }>;
      };
    };
    update: (values: Record<string, unknown>) => {
      eq: (column: string, value: unknown) => Promise<{ error: unknown }>;
    };
  };
};

type ContactSubmissionParams = {
  data: ContactInput;
  submissionKey: string;
  supabase: SupabaseLike;
  sendNotification: (data: ContactInput) => Promise<string | undefined>;
  sendVisitorConfirmation: (data: {
    kind: 'contact';
    email: string;
    name: string;
    reference: string;
  }) => Promise<unknown>;
  visitorConfirmationEnabled: boolean;
};

type ContactSubmissionResult = {
  status: number;
  body: Record<string, unknown>;
};

type ContactSubmissionLock = {
  status: 'sending' | 'sent' | 'failed';
  createdAt: number;
  result?: ContactSubmissionResult;
};

const submissionLocks = new Map<string, ContactSubmissionLock>();
const lockDurationMs = 60_000;

export async function submitContactEmailFirst({
  data,
  submissionKey,
  supabase,
  sendNotification,
  sendVisitorConfirmation,
  visitorConfirmationEnabled,
}: ContactSubmissionParams): Promise<ContactSubmissionResult> {
  const existing = submissionLocks.get(submissionKey);

  if (existing && Date.now() - existing.createdAt < lockDurationMs) {
    if (existing.status === 'sending') {
      return {
        status: 409,
        body: {
          ok: false,
          error: 'A submission with these details is already being processed.',
        },
      };
    }

    return {
      status: existing.result?.status ?? 200,
      body: {
        ...(existing.result?.body ?? { ok: true }),
        duplicate: true,
      },
    };
  }

  const finalize = (result: ContactSubmissionResult) => {
    submissionLocks.set(submissionKey, {
      status: result.status === 200 ? 'sent' : 'failed',
      createdAt: Date.now(),
      result,
    });
    return result;
  };

  submissionLocks.set(submissionKey, {
    status: 'sending',
    createdAt: Date.now(),
  });

  let notificationId: string | undefined;

  try {
    notificationId = await sendNotification(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : '';
    const isResendTestMode = message.includes('You can only send testing emails');

    return finalize({
      status: 502,
      body: {
        ok: false,
        error: isResendTestMode
          ? 'Resend test mode only allows sending to the account owner. Verify a domain and set EMAIL_FROM to an address on that domain.'
          : 'Notification delivery failed.',
        detail: serializeEmailError(error),
        notificationId,
      },
    });
  }

  let insertResult: {
    data: { id: string } | null;
    error: { message?: string } | null;
  };

  try {
    insertResult = await supabase
      .from('form_submissions')
      .insert({
        kind: 'contact',
        name: data.name,
        email: data.email,
        practice: data.practice,
        message: data.message,
        submission_key: submissionKey,
        notification_status: 'sent',
        visitor_confirmation_status: visitorConfirmationEnabled ? 'pending' : 'disabled',
      })
      .select('id')
      .single();
  } catch (error) {
    console.error('Supabase contact insert threw after Resend acceptance', {
      notificationId,
      error,
    });

    return finalize({
      status: 500,
      body: {
        ok: false,
        partialFailure: true,
        error: 'The notification email was accepted, but the enquiry could not be saved.',
        notificationId,
      },
    });
  }

  const { data: row, error } = insertResult;

  if (error || !row) {
    console.error('Supabase contact insert failed after Resend acceptance', {
      notificationId,
      error,
    });

    return finalize({
      status: 500,
      body: {
        ok: false,
        partialFailure: true,
        error: 'The notification email was accepted, but the enquiry could not be saved.',
        notificationId,
      },
    });
  }

  const id = String(row.id);

  if (visitorConfirmationEnabled) {
    try {
      await sendVisitorConfirmation({
        kind: 'contact',
        email: data.email,
        name: data.name,
        reference: id,
      });
      await supabase
        .from('form_submissions')
        .update({ visitor_confirmation_status: 'sent' })
        .eq('id', id);
    } catch (error) {
      const details = serializeEmailError(error);
      await supabase
        .from('form_submissions')
        .update({ visitor_confirmation_status: 'failed', visitor_confirmation_error: details })
        .eq('id', id);
    }
  }

  return finalize({
    status: 200,
    body: {
      ok: true,
      id,
      reference: id,
      notificationId,
    },
  });
}