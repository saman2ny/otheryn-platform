import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { contactSchema, getFieldErrors, type ContactInput } from '../lib/validation';

const contactDetails = [
  { label: 'Email', value: 'hello.otheryn@gmail.com', href: 'mailto:ramyad029@gmail.com' },
  { label: 'Phone', value: '+91 9962 194743', href: 'tel:+919962194743' },
  { label: 'Address', value: ' Door No. 1/119 (178 old), Crown SM Plaza\nVelachery Tambaram Main Road, Santhospuram,\nVengaivasal Main Road, Village, Tambaram 600073' },
];

type ContactErrors = Partial<Record<keyof ContactInput, string>>;

function ErrorText({ id, error }: { id: string; error?: string }) {
  if (!error) return null;

  return (
    <p id={`${id}-error`} className="mt-2 text-xs leading-5 text-clay" role="alert">
      {error}
    </p>
  );
}

export default function Contact() {
  const [sent, setSent] = useState<ContactInput | null>(null);
  const [errors, setErrors] = useState<ContactErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const data = new FormData(event.currentTarget);
    const result = contactSchema.safeParse({
      name: String(data.get('name') ?? ''),
      email: String(data.get('email') ?? ''),
      practice: String(data.get('practice') ?? ''),
      message: String(data.get('message') ?? ''),
    });

    if (!result.success) {
      const nextErrors = getFieldErrors(result.error);
      setErrors(nextErrors);
      setSubmitError('');
      document.getElementById(Object.keys(nextErrors)[0])?.focus();
      return;
    }

    setErrors({});
    setSubmitError('');
    setSubmitting(true);

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...result.data,
          website: String(data.get('website') ?? ''),
        }),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || !payload.ok) {
        if (payload.errors) setErrors(payload.errors as ContactErrors);
        setSubmitError(payload.error ?? 'Unable to send your message.');
        return;
      }

      setSent(result.data);
    } catch {
      setSubmitError('Unable to send your message. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <PageIntro
        index="09"
        eyebrow="Contact"
        title={<>Start a <span className="italic text-forest">conversation.</span></>}
      >
        Tell us where the day gets stuck. We will show you the shortest path to a calmer, more connected practice.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container grid gap-14 lg:grid-cols-[0.8fr_1.2fr] spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="border-t border-ink">
            {contactDetails.map((detail, index) => (
              <div key={detail.label} className="grid gap-3 border-b border-ink py-6 sm:grid-cols-[3rem_1fr]">
                <span className="font-mono text-[0.62rem] text-clay">0{index + 1}</span>
                <div>
                  <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">{detail.label}</p>
                  {detail.href ? (
                    <a href={detail.href} className="mt-2 inline-block font-display text-2xl text-ink transition hover:text-forest">
                      {detail.value}
                    </a>
                  ) : (
                    <p className="mt-2 whitespace-pre-line text-ink/70">{detail.value}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {sent ? (
            <div className="glass-panel rounded-2xl p-6 sm:p-8" aria-live="polite">
              <p className="eyebrow">Message received</p>
              <h2 className="mt-4 font-display text-[clamp(2.5rem,4vw,4.5rem)] leading-[0.95] tracking-[-0.05em] text-ink">
                Thanks, {sent.name.split(' ')[0] || 'there'}.
              </h2>
              <p className="mt-4 max-w-xl text-ink/60">
                We have your note for {sent.email}. The team will follow up with next steps and a suggested time to talk.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link to="/book" className="btn-primary">
                  Book a walkthrough
                  <span aria-hidden="true">↗</span>
                </Link>
                <button type="button" onClick={() => setSent(null)} className="btn-secondary">
                  Send another message
                </button>
              </div>
            </div>
          ) : (
            <form className="grid gap-8" onSubmit={handleSubmit} noValidate>
              <input
                type="text"
                name="website"
                tabIndex={-1}
                autoComplete="off"
                className="hidden"
                aria-hidden="true"
              />
              <div className="grid gap-8 sm:grid-cols-2">
                <div>
                  <label htmlFor="name" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                    Name
                  </label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    className="glass-field mt-2"
                    placeholder="Your name"
                    aria-invalid={Boolean(errors.name)}
                    aria-describedby={errors.name ? 'name-error' : undefined}
                  />
                  <ErrorText id="name" error={errors.name} />
                </div>
                <div>
                  <label htmlFor="email" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    className="glass-field mt-2"
                    placeholder="you@practice.com"
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                  />
                  <ErrorText id="email" error={errors.email} />
                </div>
              </div>

              <div>
                <label htmlFor="practice" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                  Practice name
                </label>
                <input
                  id="practice"
                  name="practice"
                  type="text"
                  required
                  className="glass-field mt-2"
                  placeholder="Your practice"
                  aria-invalid={Boolean(errors.practice)}
                  aria-describedby={errors.practice ? 'practice-error' : undefined}
                />
                <ErrorText id="practice" error={errors.practice} />
              </div>

              <div>
                <label htmlFor="message" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                  What is not working?
                </label>
                <textarea
                  id="message"
                  name="message"
                  rows={4}
                  required
                  className="glass-field mt-2 resize-none"
                  placeholder="Tell us about the workflow."
                  aria-invalid={Boolean(errors.message)}
                  aria-describedby={errors.message ? 'message-error' : undefined}
                />
                <ErrorText id="message" error={errors.message} />
              </div>

              {submitError && (
                <p className="text-sm leading-6 text-clay" role="alert" aria-live="polite">
                  {submitError}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:justify-self-start"
              >
                {submitting ? 'Sending…' : 'Send message'}
                {submitting ? (
                  <span
                    className="h-4 w-4 animate-spin rounded-full border-2 border-paper/40 border-t-paper"
                    aria-hidden="true"
                  />
                ) : (
                  <span aria-hidden="true">↗</span>
                )}
              </button>
            </form>
          )}
        </div>
      </section>
    </>
  );
}