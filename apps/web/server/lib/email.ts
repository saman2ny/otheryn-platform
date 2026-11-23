import { resend, resendConfigured } from './resend';

type SendPayload = {
  from: string;
  to: string;
  subject: string;
  html: string;
  replyTo?: string;
};

type ContactNotificationData = {
  name: string;
  email: string;
  practice: string;
  message: string;
};

type BookingNotificationData = {
  reference: string;
  firstName: string;
  lastName: string;
  email: string;
  practice: string;
  specialty: string;
  providers: string;
  date: string;
  time: string;
};

type VisitorConfirmationData = {
  kind: 'contact' | 'booking';
  email: string;
  name: string;
  reference?: string;
  date?: string;
  time?: string;
};

const escapeHtml = (value: string) => {
  const entities: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };

  return value.replace(/[&<>"']/g, (character) => entities[character] ?? character);
};

const getFrom = () => {
  const from = process.env.EMAIL_FROM?.trim();
  if (!from) throw new Error('EMAIL_FROM is not configured.');
  return from;
};

const getNotificationEmail = () => {
  const email =
    process.env.CONTACT_NOTIFICATION_EMAIL?.trim() || process.env.NOTIFICATION_EMAIL?.trim();
  if (!email) throw new Error('NOTIFICATION_EMAIL is not configured.');
  return email;
};

const getPublicSiteUrl = () => process.env.PUBLIC_SITE_URL ?? 'http://localhost:5173';

const formatBookingDate = (value: string) =>
  new Date(`${value}T00:00:00`).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

const formatTime = (value: string) => {
  const [hours, minutes] = value.split(':').map(Number);
  const suffix = hours >= 12 ? 'PM' : 'AM';
  const hour = hours % 12 || 12;
  return `${hour}:${String(minutes).padStart(2, '0')} ${suffix}`;
};

const shell = (content: string) => `<!doctype html>
<html lang="en">
  <body style="margin:0;background:#f2efe7;color:#17251f;font-family:Helvetica,Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;">Otheryn notification</div>
    <div style="padding:32px 16px;">
      <div style="max-width:560px;margin:0 auto;overflow:hidden;border:1px solid rgba(255,255,255,0.6);border-radius:20px;background:#fbfaf6;box-shadow:0 24px 80px -32px rgba(23,37,31,0.45);">
        ${content}
      </div>
    </div>
  </body>
</html>`;

const businessShell = (title: string, rows: Array<[string, string]>) =>
  shell(`
    <div style="background:#1c4b3a;padding:28px;">
      <p style="margin:0 0 10px;color:#d8ef68;font:600 11px/1.2 SFMono-Regular,Consolas,monospace;letter-spacing:0.18em;text-transform:uppercase;">Otheryn</p>
      <h1 style="margin:0;color:#f2efe7;font:400 34px/1.1 Georgia,serif;letter-spacing:-0.04em;">${escapeHtml(title)}</h1>
    </div>
    <div style="padding:28px;">
      ${rows
        .map(
          ([label, value]) => `
        <div style="padding:14px 0;border-bottom:1px solid rgba(23,37,31,0.12);">
          <p style="margin:0 0 6px;color:rgba(23,37,31,0.5);font:600 10px/1.2 SFMono-Regular,Consolas,monospace;letter-spacing:0.14em;text-transform:uppercase;">${escapeHtml(label)}</p>
          <p style="margin:0;color:#17251f;font-size:15px;line-height:1.6;white-space:pre-line;">${escapeHtml(value)}</p>
        </div>`,
        )
        .join('')}
    </div>`);

const visitorShell = (content: string) =>
  shell(`
    <div style="background:#1c4b3a;padding:28px;">
      <p style="margin:0 0 10px;color:#d8ef68;font:600 11px/1.2 SFMono-Regular,Consolas,monospace;letter-spacing:0.18em;text-transform:uppercase;">Otheryn</p>
      <h1 style="margin:0;color:#f2efe7;font:400 34px/1.1 Georgia,serif;letter-spacing:-0.04em;">You're on the list.</h1>
    </div>
    <div style="padding:28px;">
      ${content}
      <a href="${escapeHtml(getPublicSiteUrl())}" style="display:inline-block;margin-top:24px;background:#1c4b3a;color:#f2efe7;padding:12px 18px;border-radius:8px;font:600 11px/1 SFMono-Regular,Consolas,monospace;letter-spacing:0.14em;text-transform:uppercase;text-decoration:none;">Visit Otheryn</a>
    </div>`);

const send = async (payload: SendPayload) => {
  if (!resend || !resendConfigured) {
    throw new Error('Resend is not configured.');
  }

  const { data, error } = await resend.emails.send(payload);
  if (error) throw new Error(error.message);
  return data?.id;
};

export const serializeEmailError = (error: unknown) => {
  const details: Record<string, unknown> = {
    name: error instanceof Error ? error.name : 'Error',
    message: error instanceof Error ? error.message : 'Email delivery failed.',
  };

  if (typeof error === 'object' && error !== null) {
    const candidate = error as { statusCode?: unknown; status?: unknown };
    if (candidate.statusCode !== undefined) details.statusCode = candidate.statusCode;
    if (candidate.status !== undefined) details.status = candidate.status;
  }

  return JSON.stringify(details);
};

export const sendContactNotification = async (data: ContactNotificationData) => {
  const from = getFrom();
  const to = getNotificationEmail();

  return send({
    from,
    to,
    replyTo: data.email,
    subject: `New Otheryn contact request — ${data.name}`,
    html: businessShell('New contact request', [
      ['Name', data.name],
      ['Email', data.email],
      ['Practice', data.practice],
      ['Message', data.message],
    ]),
  });
};

export const sendBookingNotification = async (data: BookingNotificationData) => {
  const from = getFrom();
  const to = getNotificationEmail();

  return send({
    from,
    to,
    replyTo: data.email,
    subject: `New Otheryn walkthrough — ${data.firstName} ${data.lastName}`,
    html: businessShell('New walkthrough request', [
      ['Name', `${data.firstName} ${data.lastName}`],
      ['Email', data.email],
      ['Practice', data.practice],
      ['Specialty', data.specialty],
      ['Providers', data.providers],
      ['Preferred date', formatBookingDate(data.date)],
      ['Preferred time', formatTime(data.time)],
      ['Reference', data.reference],
    ]),
  });
};

export const sendWalkthroughNotification = async (data: BookingNotificationData) => {
  const from = getFrom();
  const to = getNotificationEmail();

  return send({
    from,
    to,
    replyTo: data.email,
    subject: 'New Otheryn Walkthrough Request',
    html: businessShell('New walkthrough request', [
      ['Name', `${data.firstName} ${data.lastName}`],
      ['Email', data.email],
      ['Practice', data.practice],
      ['Specialty', data.specialty],
      ['Providers', data.providers],
      ['Preferred date', formatBookingDate(data.date)],
      ['Preferred time', formatTime(data.time)],
      ['Reference', data.reference],
    ]),
  });
};

export const sendVisitorConfirmation = async (data: VisitorConfirmationData) => {
  if (process.env.VISITOR_CONFIRMATION_ENABLED !== 'true') return null;

  const from = process.env.VISITOR_CONFIRMATION_FROM_EMAIL || getFrom();
  const replyTo = getNotificationEmail();

  const content =
    data.kind === 'booking'
      ? `<p style="margin:0 0 16px;color:rgba(23,37,31,0.7);font-size:16px;line-height:1.7;">Thanks, ${escapeHtml(data.name)}. Your Otheryn walkthrough request is booked.</p>
         <p style="margin:0 0 8px;color:rgba(23,37,31,0.55);font:600 10px/1.2 SFMono-Regular,Consolas,monospace;letter-spacing:0.14em;text-transform:uppercase;">When</p>
         <p style="margin:0 0 18px;color:#17251f;font-size:16px;line-height:1.6;">${escapeHtml(formatBookingDate(data.date ?? ''))} · ${escapeHtml(formatTime(data.time ?? ''))}</p>
         <p style="margin:0;color:rgba(23,37,31,0.55);font-size:14px;line-height:1.6;">Reference ${escapeHtml(data.reference ?? '')}</p>`
      : `<p style="margin:0 0 16px;color:rgba(23,37,31,0.7);font-size:16px;line-height:1.7;">Thanks, ${escapeHtml(data.name)}. We received your message and the team will follow up.</p>
         <p style="margin:0;color:rgba(23,37,31,0.55);font-size:14px;line-height:1.6;">We usually reply within one business day.</p>`;

  return send({
    from,
    to: data.email,
    replyTo,
    subject:
      data.kind === 'booking'
        ? 'Your Otheryn walkthrough request'
        : 'We received your Otheryn message',
    html: visitorShell(content),
  });
};