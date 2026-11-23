import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import SpecialtySelect from '../components/SpecialtySelect';
import ProvidersSelect from '../components/ProvidersSelect';
import {
  bookingSchema,
  bookingTimeSlots,
  getFieldErrors,
  today,
  type BookingInput,
} from '../lib/validation';

const steps = [
  { title: 'A 30-minute walkthrough', desc: 'We use a workflow close to yours, not a generic slide deck.' },
  { title: 'A clear implementation path', desc: 'You leave with the data, integrations, and rollout steps that matter.' },
  { title: 'A direct line to the team', desc: 'No handoff maze. You talk to the people building the product.' },
];

type Booking = BookingInput & {
  reference: string;
};

type BookingErrors = Partial<Record<keyof BookingInput, string>>;

const formatDate = (value: string) =>
  new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

const formatTime = (value: string) => {
  const [hours, minutes] = value.split(':').map(Number);
  const suffix = hours >= 12 ? 'PM' : 'AM';
  const hour = hours % 12 || 12;
  return `${hour}:${String(minutes).padStart(2, '0')} ${suffix}`;
};

const toCalendarDate = (date: Date) =>
  date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

function ErrorText({ id, error }: { id: string; error?: string }) {
  if (!error) return null;

  return (
    <p id={`${id}-error`} className="mt-2 text-xs leading-5 text-clay" role="alert">
      {error}
    </p>
  );
}

const fieldClass = (hasError: boolean) =>
  `mt-2 w-full rounded-xl border bg-white/60 px-4 py-3 text-ink backdrop-blur-md transition placeholder:text-ink/50 hover:border-ink/35 focus:border-forest/60 focus:outline-none focus:ring-2 focus:ring-forest/20 user-valid:border-forest/40 disabled:cursor-not-allowed disabled:bg-white/30 disabled:text-ink/40 ${
    hasError ? 'border-clay/70 focus:border-clay focus:ring-clay/20' : 'border-ink/20'
  }`;

export default function Booking() {
  const [time, setTime] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [providers, setProviders] = useState('');
  const [booking, setBooking] = useState<Booking | null>(null);
  const [errors, setErrors] = useState<BookingErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const data = new FormData(event.currentTarget);
    const result = bookingSchema.safeParse({
      firstName: String(data.get('firstName') ?? ''),
      lastName: String(data.get('lastName') ?? ''),
      email: String(data.get('email') ?? ''),
      practice: String(data.get('practice') ?? ''),
      specialty,
      providers,
      date: String(data.get('date') ?? ''),
      time,
    });

    if (!result.success) {
      const nextErrors = getFieldErrors(result.error);
      setErrors(nextErrors);
      setSubmitError('');

      const firstError = Object.keys(nextErrors)[0];
      if (firstError === 'time') {
        document.querySelector<HTMLButtonElement>('button[aria-pressed]')?.focus();
      } else {
        document.getElementById(firstError)?.focus();
      }
      return;
    }

    setErrors({});
    setSubmitError('');
    setSubmitting(true);

    try {
      const response = await fetch('/api/booking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...result.data,
          website: String(data.get('website') ?? ''),
        }),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || !payload.ok) {
        if (payload.errors) setErrors(payload.errors as BookingErrors);
        setSubmitError(payload.error ?? 'Unable to book the walkthrough.');
        return;
      }

      setBooking({
        ...result.data,
        reference: String(payload.reference ?? payload.id ?? ''),
      });
    } catch {
      setSubmitError('Unable to book the walkthrough. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const addToCalendar = () => {
    if (!booking) return;

    const start = new Date(`${booking.date}T${booking.time}:00`);
    const end = new Date(start.getTime() + 30 * 60 * 1000);
    const calendar = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Otheryn//Walkthrough//EN',
      'BEGIN:VEVENT',
      `UID:${booking.reference}@otheryn.com`,
      `DTSTAMP:${toCalendarDate(new Date())}`,
      `DTSTART:${toCalendarDate(start)}`,
      `DTEND:${toCalendarDate(end)}`,
      'SUMMARY:Otheryn walkthrough',
      'DESCRIPTION:30-minute Otheryn walkthrough',
      'END:VEVENT',
      'END:VCALENDAR',
    ].join('\r\n');

    const blob = new Blob([calendar], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `otheryn-walkthrough-${booking.reference}.ics`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const resetBooking = () => {
    setBooking(null);
    setTime('');
    setSpecialty('');
    setProviders('');
    setErrors({});
  };

  return (
    <>
      <PageIntro
        index="12"
        eyebrow="Book a walkthrough"
        title={<>See it with <span className="italic text-forest">your patients.</span></>}
      >
        A working session built around your specialty, your systems, and the parts of the day that need the most help.
      </PageIntro>

      <section className="section bg-transparent">
        <div className="container grid gap-14 lg:grid-cols-[0.8fr_1.2fr]">
          <aside className="rounded-2xl border border-white/10 bg-forest p-7 text-paper shadow-[0_30px_80px_-30px_rgba(0,0,0,0.55)] lg:p-10">
            <p className="eyebrow flex items-center gap-3 text-paper/65">
              <span className="h-px w-8 bg-citrus" />
              What happens next
            </p>
            <ol className="mt-8 space-y-6">
              {steps.map((step, index) => (
                <li key={step.title} className="grid grid-cols-[2.5rem_1fr] gap-4 border-t border-paper/20 pt-5">
                  <span className="font-mono text-[0.6rem] text-citrus">0{index + 1}</span>
                  <div>
                    <h2 className="font-display text-2xl leading-none tracking-[-0.025em] text-paper">{step.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-paper/80">{step.desc}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-10 border-t border-paper/20 pt-5 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-paper/60">
              No slideware. Your workflows.
            </p>
          </aside>

          <div>
            {booking ? (
              <div className="rounded-2xl border border-ink/10 bg-bone p-6 shadow-[0_30px_90px_-40px_rgba(23,37,31,0.4)] sm:p-8" aria-live="polite">
                <p className="eyebrow">Booking confirmed</p>
                <h2 className="mt-4 font-display text-[clamp(2.5rem,4vw,4.5rem)] leading-[0.95] tracking-[-0.05em] text-ink">
                  You’re on the calendar.
                </h2>
                <p className="mt-4 max-w-xl text-ink/60">
                  We’ve reserved a 30-minute walkthrough for {booking.firstName}. A calendar file is ready to download.
                </p>

                <div className="mt-8 grid gap-5 border-y border-ink/15 py-6 sm:grid-cols-2">
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Reference</p>
                    <p className="mt-2 font-mono text-sm text-ink">{booking.reference}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">When</p>
                    <p className="mt-2 text-ink">{formatDate(booking.date)} · {formatTime(booking.time)}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Practice</p>
                    <p className="mt-2 text-ink">{booking.practice}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Specialty</p>
                    <p className="mt-2 text-ink">{booking.specialty}</p>
                  </div>
                </div>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <button type="button" onClick={addToCalendar} className="btn-primary">
                    Add to calendar
                    <span aria-hidden="true">↓</span>
                  </button>
                  <button type="button" onClick={resetBooking} className="btn-secondary">
                    Book another time
                  </button>
                </div>

                <p className="mt-6 text-sm leading-6 text-ink/50">
                  Confirmation details are prepared for {booking.email}. You can close this page or download the calendar invite.
                </p>
              </div>
            ) : (
              <form className="grid gap-8 rounded-2xl border border-ink/10 bg-bone p-6 shadow-[0_30px_90px_-40px_rgba(23,37,31,0.4)] sm:p-8" onSubmit={handleSubmit} noValidate>
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
                    <label htmlFor="first-name" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                      First name
                    </label>
                    <input
                      id="firstName"
                      name="firstName"
                      type="text"
                      required
                      className={fieldClass(Boolean(errors.firstName))}
                      placeholder="Amina"
                      aria-invalid={Boolean(errors.firstName)}
                      aria-describedby={errors.firstName ? 'firstName-error' : undefined}
                    />
                    <ErrorText id="firstName" error={errors.firstName} />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                      Last name
                    </label>
                    <input
                      id="lastName"
                      name="lastName"
                      type="text"
                      required
                      className={fieldClass(Boolean(errors.lastName))}
                      placeholder="Rahman"
                      aria-invalid={Boolean(errors.lastName)}
                      aria-describedby={errors.lastName ? 'lastName-error' : undefined}
                    />
                    <ErrorText id="lastName" error={errors.lastName} />
                  </div>
                </div>

                <div>
                  <label htmlFor="email" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                    Work email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    className={fieldClass(Boolean(errors.email))}
                    placeholder="amina@practice.com"
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                  />
                  <ErrorText id="email" error={errors.email} />
                </div>

                <div>
                  <label htmlFor="practice" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                    Practice name
                  </label>
                  <input
                    id="practice"
                    name="practice"
                    type="text"
                    required
                    className={fieldClass(Boolean(errors.practice))}
                    placeholder="Your practice"
                    aria-invalid={Boolean(errors.practice)}
                    aria-describedby={errors.practice ? 'practice-error' : undefined}
                  />
                  <ErrorText id="practice" error={errors.practice} />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-6">
                  <div className="min-w-0">
                    <label
                      id="specialty-label"
                      htmlFor="specialty"
                      className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70"
                    >
                      Specialty
                    </label>
                    <SpecialtySelect
                      value={specialty}
                      onChange={(value) => {
                        setSpecialty(value);
                        setErrors((previous) => ({ ...previous, specialty: undefined }));
                      }}
                      error={Boolean(errors.specialty)}
                    />
                    <ErrorText id="specialty" error={errors.specialty} />
                  </div>
                  <div className="min-w-0">
                    <label
                      id="providers-label"
                      htmlFor="providers"
                      className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70"
                    >
                      Providers
                    </label>
                    <ProvidersSelect
                      value={providers}
                      onChange={(value) => {
                        setProviders(value);
                        setErrors((previous) => ({ ...previous, providers: undefined }));
                      }}
                      error={Boolean(errors.providers)}
                    />
                    <ErrorText id="providers" error={errors.providers} />
                  </div>
                </div>

                <div>
                  <label htmlFor="date" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                    Preferred date
                  </label>
                  <input
                    id="date"
                    name="date"
                    type="date"
                    required
                    min={today}
                    className={fieldClass(Boolean(errors.date))}
                    aria-invalid={Boolean(errors.date)}
                    aria-describedby={errors.date ? 'date-error' : undefined}
                  />
                  <ErrorText id="date" error={errors.date} />
                </div>

                <div>
                  <p id="time-label" className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/70">
                    Preferred time
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5" role="group" aria-labelledby="time-label">
                    {bookingTimeSlots.map((slot) => (
                      <button
                        key={slot}
                        type="button"
                        onClick={() => {
                          setTime(slot);
                          setErrors((previous) => ({ ...previous, time: undefined }));
                        }}
                        aria-pressed={time === slot}
                        className={`border px-3 py-3 font-mono text-[0.6rem] uppercase tracking-[0.12em] transition focus:outline-none focus:ring-2 focus:ring-forest/30 ${
                          time === slot
                            ? 'border-forest bg-forest text-paper shadow-[0_12px_30px_-14px_rgba(28,75,58,0.7)]'
                            : 'border-ink/20 bg-white/60 text-ink hover:border-forest/40 hover:bg-white/80'
                        }`}
                      >
                        {formatTime(slot)}
                      </button>
                    ))}
                  </div>
                  <ErrorText id="time" error={errors.time} />
                </div>

                {submitError && (
                  <p className="text-sm leading-6 text-clay" role="alert" aria-live="polite">
                    {submitError}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex w-full items-center justify-center gap-2 bg-forest px-6 py-4 font-mono text-[0.65rem] font-medium uppercase tracking-[0.14em] text-paper shadow-[0_18px_40px_-18px_rgba(28,75,58,0.7)] transition hover:-translate-y-0.5 hover:bg-ink focus:outline-none focus:ring-2 focus:ring-clay focus:ring-offset-2 focus:ring-offset-bone disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:justify-self-start"
                >
                  {submitting ? 'Booking…' : 'Book walkthrough'}
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

            {!booking && (
              <p className="mt-8 max-w-xl text-sm leading-6 text-ink/50">
                By submitting, you agree to our{' '}
                <Link to="/privacy" className="border-b border-ink/30 text-ink transition hover:border-ink">
                  Privacy Policy
                </Link>{' '}
                and{' '}
                <Link to="/terms" className="border-b border-ink/30 text-ink transition hover:border-ink">
                  Terms of Service
                </Link>
                .
              </p>
            )}
          </div>
        </div>
      </section>
    </>
  );
}