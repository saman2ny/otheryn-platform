import './lib/loadEnv';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import helmet from 'helmet';
import { createRateLimitMiddleware } from './lib/rateLimits';
import {
  bookingSchema,
  contactSchema,
  getFieldErrors,
  walkthroughSchema,
} from '../src/lib/validation';
import {
  sendBookingNotification,
  sendContactNotification,
  sendVisitorConfirmation,
  sendWalkthroughNotification,
  serializeEmailError,
} from './lib/email';
import { supabase, supabaseConfigError, supabaseConfigured } from './lib/supabase';
import { submitContactEmailFirst } from './lib/contactSubmission';
import { submitWalkthrough } from './lib/walkthroughSubmission';

const app = express();
const port = Number(process.env.PORT ?? 3001);
const isProduction = process.env.NODE_ENV === 'production';
// Production default: database-first. Development default: email-first.
const contactEmailFirst =
  process.env.CONTACT_EMAIL_FIRST === 'true' ||
  (!isProduction && process.env.CONTACT_EMAIL_FIRST !== 'false');
const currentDir = path.dirname(fileURLToPath(import.meta.url));
const distPath = path.resolve(currentDir, '../dist');

app.disable('x-powered-by');
app.set('trust proxy', 1);
app.use(helmet({ contentSecurityPolicy: false }));
app.use(express.json({ limit: '16kb' }));
app.use('/api/contact', createRateLimitMiddleware('contact'));
app.use('/api/booking', createRateLimitMiddleware('booking'));
app.use('/api/walkthrough', createRateLimitMiddleware('walkthrough'));

const createReference = () => `OY-${Date.now().toString(36).toUpperCase().slice(-6)}`;

const createSubmissionKey = (kind: string, data: unknown) =>
  createHash('sha256').update(JSON.stringify({ kind, data })).digest('hex');

const isHoneypot = (body: Record<string, unknown>) =>
  typeof body.website === 'string' && body.website.trim().length > 0;

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    resendConfigured: Boolean(process.env.RESEND_API_KEY),
    supabaseConfigured,
    supabaseConfigError,
  });
});

app.post('/api/contact', async (req, res) => {
  try {
    if (isHoneypot(req.body ?? {})) {
      return res.status(400).json({ ok: false, error: 'Unable to accept this submission.' });
    }

    const parsed = contactSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        ok: false,
        error: 'Validation failed.',
        errors: getFieldErrors(parsed.error),
      });
    }

    if (!supabase || !supabaseConfigured) {
      return res.status(503).json({
        ok: false,
        error: 'The submission service is not configured.',
        detail: supabaseConfigError,
      });
    }

    const data = parsed.data;
    const submissionKey = createSubmissionKey('contact', data);

    if (contactEmailFirst) {
      const result = await submitContactEmailFirst({
        data,
        submissionKey,
        supabase: supabase as never,
        sendNotification: sendContactNotification,
        sendVisitorConfirmation,
        visitorConfirmationEnabled: process.env.VISITOR_CONFIRMATION_ENABLED === 'true',
      });

      return res.status(result.status).json(result.body);
    }

    const { data: row, error } = await supabase
      .from('form_submissions')
      .insert({
        kind: 'contact',
        name: data.name,
        email: data.email,
        practice: data.practice,
        message: data.message,
        submission_key: submissionKey,
        notification_status: 'pending',
        visitor_confirmation_status:
          process.env.VISITOR_CONFIRMATION_ENABLED === 'true' ? 'pending' : 'disabled',
      })
      .select('id')
      .single();

    if (error || !row) {
      if (error?.code === '23505') {
      const { data: existing } = await supabase
        .from('form_submissions')
        .select('id, notification_status')
        .eq('submission_key', submissionKey)
        .single();

      if (existing?.notification_status === 'failed') {
        try {
          const notificationId = await sendContactNotification(data);
          await supabase
            .from('form_submissions')
            .update({ notification_status: 'sent', notification_error: null })
            .eq('id', existing.id);

          return res.status(200).json({
            ok: true,
            id: existing.id,
            reference: existing.id,
            retried: true,
            notificationId,
          });
        } catch (emailError) {
          const details = serializeEmailError(emailError);
          const message = emailError instanceof Error ? emailError.message : '';
          const isResendTestMode = message.includes('You can only send testing emails');
          console.error('Contact notification retry failed', details);
          await supabase
            .from('form_submissions')
            .update({ notification_status: 'failed', notification_error: details })
            .eq('id', existing.id);

          return res.status(502).json({
            ok: false,
            error: isResendTestMode
              ? 'Resend test mode only allows sending to the account owner. Verify a domain and set EMAIL_FROM to an address on that domain.'
              : 'We saved your request, but the notification email failed.',
            reference: existing.id,
          });
        }
      }

      return res.status(409).json({
        ok: false,
        error: 'A submission with these details was already received.',
      });
    }

    console.error('Supabase contact insert failed', error);
      const missingTable = error?.message?.includes('Could not find the table');
      return res.status(500).json({
        ok: false,
        error: missingTable
          ? 'The form_submissions table is missing. Apply supabase/schema.sql.'
          : 'Unable to save the submission.',
      });
    }

    const id = String(row.id);

    let notificationId: string | undefined;

    try {
      notificationId = await sendContactNotification(data);
      await supabase.from('form_submissions').update({ notification_status: 'sent' }).eq('id', id);
    } catch (emailError) {
      const details = serializeEmailError(emailError);
      const message = emailError instanceof Error ? emailError.message : '';
      const isResendTestMode = message.includes('You can only send testing emails');
      console.error('Contact notification failed', details);
      await supabase
        .from('form_submissions')
        .update({ notification_status: 'failed', notification_error: details })
        .eq('id', id);
      return res.status(502).json({
        ok: false,
        error: isResendTestMode
          ? 'Resend test mode only allows sending to the account owner. Verify a domain and set EMAIL_FROM to an address on that domain.'
          : 'We saved your request, but the notification email failed.',
        reference: id,
      });
    }

    if (process.env.VISITOR_CONFIRMATION_ENABLED === 'true') {
      try {
        await sendVisitorConfirmation({ kind: 'contact', email: data.email, name: data.name, reference: id });
        await supabase
          .from('form_submissions')
          .update({ visitor_confirmation_status: 'sent' })
          .eq('id', id);
      } catch (confirmationError) {
        const message =
          confirmationError instanceof Error ? confirmationError.message : 'Confirmation email failed.';
        await supabase
          .from('form_submissions')
          .update({ visitor_confirmation_status: 'failed', visitor_confirmation_error: message })
          .eq('id', id);
      }
    }

    return res.status(200).json({ ok: true, id, reference: id, notificationId });
  } catch (error) {
    console.error('Contact endpoint failed', error);
    return res.status(500).json({ ok: false, error: 'Unexpected server error.' });
  }
});

app.post('/api/booking', async (req, res) => {
  try {
    if (isHoneypot(req.body ?? {})) {
      return res.status(400).json({ ok: false, error: 'Unable to accept this submission.' });
    }

    const parsed = bookingSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        ok: false,
        error: 'Validation failed.',
        errors: getFieldErrors(parsed.error),
      });
    }

    if (!supabase || !supabaseConfigured) {
      return res.status(503).json({
        ok: false,
        error: 'The submission service is not configured.',
        detail: supabaseConfigError,
      });
    }

    const data = parsed.data;
    const reference = createReference();
    const submissionKey = createSubmissionKey('booking', data);

    const { data: row, error } = await supabase
      .from('form_submissions')
      .insert({
        kind: 'booking',
        reference,
        name: `${data.firstName} ${data.lastName}`,
        email: data.email,
        practice: data.practice,
        specialty: data.specialty,
        providers: data.providers,
        preferred_date: data.date,
        preferred_time: data.time,
        submission_key: submissionKey,
        notification_status: 'pending',
        visitor_confirmation_status:
          process.env.VISITOR_CONFIRMATION_ENABLED === 'true' ? 'pending' : 'disabled',
      })
      .select('id')
      .single();

    if (error || !row) {
      if (error?.code === '23505') {
      const { data: existing } = await supabase
        .from('form_submissions')
        .select('id, notification_status, reference')
        .eq('submission_key', submissionKey)
        .single();

      if (existing?.notification_status === 'failed') {
        try {
          await sendBookingNotification({
            ...data,
            reference: String(existing.reference ?? reference),
          });
          await supabase
            .from('form_submissions')
            .update({ notification_status: 'sent', notification_error: null })
            .eq('id', existing.id);

          return res.status(200).json({
            ok: true,
            id: existing.id,
            reference: existing.reference ?? reference,
            retried: true,
          });
        } catch (emailError) {
          const details = serializeEmailError(emailError);
          const message = emailError instanceof Error ? emailError.message : '';
          const isResendTestMode = message.includes('You can only send testing emails');
          console.error('Booking notification retry failed', details);
          await supabase
            .from('form_submissions')
            .update({ notification_status: 'failed', notification_error: details })
            .eq('id', existing.id);

          return res.status(502).json({
            ok: false,
            error: isResendTestMode
              ? 'Resend test mode only allows sending to the account owner. Verify a domain and set EMAIL_FROM to an address on that domain.'
              : 'We saved your request, but the notification email failed.',
            reference: existing.reference ?? reference,
          });
        }
      }

      return res.status(409).json({
        ok: false,
        error: 'A submission with these details was already received.',
      });
    }

    console.error('Supabase booking insert failed', error);
      const missingTable = error?.message?.includes('Could not find the table');
      return res.status(500).json({
        ok: false,
        error: missingTable
          ? 'The form_submissions table is missing. Apply supabase/schema.sql.'
          : 'Unable to save the booking request.',
      });
    }

    const id = String(row.id);

    try {
      await sendBookingNotification({ ...data, reference });
      await supabase.from('form_submissions').update({ notification_status: 'sent' }).eq('id', id);
    } catch (emailError) {
      const details = serializeEmailError(emailError);
      const message = emailError instanceof Error ? emailError.message : '';
      const isResendTestMode = message.includes('You can only send testing emails');
      console.error('Booking notification failed', details);
      await supabase
        .from('form_submissions')
        .update({ notification_status: 'failed', notification_error: details })
        .eq('id', id);
      return res.status(502).json({
        ok: false,
        error: isResendTestMode
          ? 'Resend test mode only allows sending to the account owner. Verify a domain and set EMAIL_FROM to an address on that domain.'
          : 'We saved your request, but the notification email failed.',
        reference,
      });
    }

    if (process.env.VISITOR_CONFIRMATION_ENABLED === 'true') {
      try {
        await sendVisitorConfirmation({
          kind: 'booking',
          email: data.email,
          name: data.firstName,
          reference,
          date: data.date,
          time: data.time,
        });
        await supabase
          .from('form_submissions')
          .update({ visitor_confirmation_status: 'sent' })
          .eq('id', id);
      } catch (confirmationError) {
        const message =
          confirmationError instanceof Error ? confirmationError.message : 'Confirmation email failed.';
        await supabase
          .from('form_submissions')
          .update({ visitor_confirmation_status: 'failed', visitor_confirmation_error: message })
          .eq('id', id);
      }
    }

    return res.status(200).json({ ok: true, id, reference });
  } catch (error) {
    console.error('Booking endpoint failed', error);
    return res.status(500).json({ ok: false, error: 'Unexpected server error.' });
  }
});

app.post('/api/walkthrough', async (req, res) => {
  try {
    if (isHoneypot(req.body ?? {})) {
      return res.status(400).json({ ok: false, error: 'Unable to accept this submission.' });
    }

    const parsed = walkthroughSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        ok: false,
        error: 'Validation failed.',
        errors: getFieldErrors(parsed.error),
      });
    }

    if (!supabase || !supabaseConfigured) {
      return res.status(503).json({
        ok: false,
        error: 'The submission service is not configured.',
        detail: supabaseConfigError,
      });
    }

    const data = parsed.data;
    const reference = createReference();
    const submissionKey = createSubmissionKey('walkthrough', data);

    const result = await submitWalkthrough({
      data,
      submissionKey,
      reference,
      supabase: supabase as never,
      sendNotification: sendWalkthroughNotification,
    });

    return res.status(result.status).json(result.body);
  } catch (error) {
    console.error('Walkthrough endpoint failed', error);
    return res.status(500).json({ ok: false, error: 'Unexpected server error.' });
  }
});

app.use((_req, res, next) => {
  if (res.headersSent) return next();
  if (_req.path.startsWith('/api')) {
    return res.status(404).json({ ok: false, error: 'Not found.' });
  }
  next();
});

app.use(express.static(distPath));
app.use((req, res, next) => {
  if (req.method === 'GET' && !req.path.startsWith('/api')) {
    return res.sendFile(path.join(distPath, 'index.html'));
  }
  next();
});

app.use((error: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('Unhandled server error', error);
  if (res.headersSent) return;
  res.status(500).json({ ok: false, error: 'Unexpected server error.' });
});

if (supabase) {
  const activeSupabase = supabase;
  const cleanupRateLimits = async () => {
    const { error } = await activeSupabase.rpc('cleanup_rate_limit_buckets');
    if (error) {
      console.error('Rate limit cleanup failed', {
        code: error.code,
        message: error.message,
        details: error.details,
        hint: error.hint,
      });
    }
  };

  void cleanupRateLimits();
  const cleanupTimer = setInterval(() => {
    void cleanupRateLimits();
  }, 60 * 60 * 1000);
  cleanupTimer.unref();
}

app.listen(port, () => {
  const sender = process.env.EMAIL_FROM?.trim();
  const notificationRecipient = process.env.NOTIFICATION_EMAIL?.trim();
  console.log(`Email sender: ${sender || 'not configured'}`);
  console.log(`Notification recipient: ${notificationRecipient || 'not configured'}`);
  console.log(`Otheryn API listening on http://127.0.0.1:${port}`);
});