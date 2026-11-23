import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { pricingPlans } from '../data';
import { checkoutSchema, getFieldErrors, type CheckoutInput } from '../lib/validation';

type Receipt = {
  reference: string;
  email: string;
  plan: string;
  amount: string;
  date: string;
};

type FormErrors = Partial<Record<keyof CheckoutInput, string>>;

const emptyForm: CheckoutInput = {
  email: '',
  cardName: '',
  cardNumber: '',
  expiry: '',
  cvc: '',
};

const formatCardNumber = (value: string) =>
  value
    .replace(/\D/g, '')
    .slice(0, 16)
    .replace(/(.{4})/g, '$1 ')
    .trim();

const formatExpiry = (value: string) => {
  const digits = value.replace(/\D/g, '').slice(0, 4);
  return digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
};

const createReference = () => `OY-${Date.now().toString(36).toUpperCase().slice(-6)}`;

const fieldClass = (hasError: boolean) =>
  `glass-field mt-2 border-ink/20 placeholder:text-ink/45 focus:border-forest/60 ${
    hasError ? 'border-clay/70 focus:border-clay' : ''
  }`;

type FieldProps = {
  id: string;
  label: string;
  error?: string;
  children: ReactNode;
};

function Field({ id, label, error, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/70">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="mt-2 text-xs leading-5 text-clay" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default function Checkout() {
  const [searchParams] = useSearchParams();
  const requestedPlan = (searchParams.get('plan') ?? 'professional').toLowerCase();
  const plan = pricingPlans.find((item) => item.name.toLowerCase() === requestedPlan) ?? pricingPlans[1];

  const [status, setStatus] = useState<'idle' | 'processing' | 'success'>('idle');
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [form, setForm] = useState<CheckoutInput>(emptyForm);
  const [errors, setErrors] = useState<FormErrors>({});

  const updateField = (field: keyof CheckoutInput, value: string) => {
    setForm((previous) => ({ ...previous, [field]: value }));
    setErrors((previous) => ({ ...previous, [field]: undefined }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const result = checkoutSchema.safeParse(form);

    if (!result.success) {
      const nextErrors = getFieldErrors(result.error);
      setErrors(nextErrors);

      const firstError = Object.keys(nextErrors)[0];
      document.getElementById(firstError)?.focus();
      return;
    }

    setErrors({});
    const { email } = result.data;

    setStatus('processing');
    await new Promise((resolve) => setTimeout(resolve, 1200));

    const value: Receipt = {
      reference: createReference(),
      email,
      plan: plan.name,
      amount: plan.price,
      date: new Date().toISOString(),
    };

    setReceipt(value);
    setStatus('success');
    try {
      localStorage.setItem('otheryn-receipt', JSON.stringify(value));
    } catch {
      // Receipt download still works when storage is unavailable.
    }
  };

  const downloadReceipt = () => {
    if (!receipt) return;

    const text = [
      'OTHERYN RECEIPT',
      '------------------------------------------------',
      `Reference: ${receipt.reference}`,
      `Plan: ${receipt.plan}`,
      `Amount: ${receipt.amount}/month`,
      `Billing email: ${receipt.email}`,
      `Date: ${new Date(receipt.date).toLocaleString()}`,
      '------------------------------------------------',
    ].join('\n');

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `otheryn-receipt-${receipt.reference}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (plan.name === 'Enterprise') {
    return (
      <>
        <PageIntro
          index="16"
          eyebrow="Enterprise"
          title={<>Let’s scope <span className="italic text-forest">your rollout.</span></>}
        >
          Enterprise plans are scoped with our team. Tell us about your locations, systems, and timeline.
        </PageIntro>

        <section className="section bg-transparent">
          <div className="container max-w-3xl spatial-surface py-10 sm:py-14">
            <h2 className="font-display text-4xl leading-none tracking-[-0.04em] text-ink">Talk to sales</h2>
            <p className="mt-4 max-w-xl text-ink/60">
              Enterprise pricing is custom. We’ll map the implementation, security review, and commercial structure with you.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/contact" className="btn-primary">
                Contact sales
                <span aria-hidden="true">↗</span>
              </Link>
              <Link to="/pricing" className="btn-secondary">
                Back to pricing
              </Link>
            </div>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <PageIntro
        index="16"
        eyebrow="Secure checkout"
        title={<>Activate <span className="italic text-forest">your plan.</span></>}
      >
        Start your Otheryn subscription. Your plan includes onboarding, data migration support, and security review documentation.
      </PageIntro>

      <section className="section bg-transparent">
        <div className="container grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <aside className="relative overflow-hidden rounded-3xl border border-white/10 bg-forest p-6 text-paper shadow-[0_40px_100px_-30px_rgba(23,37,31,0.65)] sm:p-8 lg:p-10">
            <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-citrus/10 blur-3xl" />

            <div className="relative">
              <div className="flex items-center justify-between gap-4">
                <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-paper/55">Order summary</p>
                <span className="border border-paper/20 px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] text-paper/70">
                  Monthly
                </span>
              </div>

              <div className="mt-8">
                <h2 className="font-display text-4xl leading-none tracking-[-0.04em] text-paper sm:text-5xl">{plan.name}</h2>
                <p className="mt-2 text-sm text-paper/70">{plan.desc}</p>
              </div>

              <div className="mt-8 flex items-baseline gap-2">
                <span className="font-display text-7xl leading-none tracking-[-0.06em] text-paper">{plan.price}</span>
                <span className="font-mono text-sm text-paper/60">{plan.period}</span>
              </div>

              <div className="mt-8 border-t border-paper/20 pt-6">
                <p className="font-mono text-[0.55rem] uppercase tracking-[0.16em] text-paper/50">Included</p>
                <ul className="mt-4 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm leading-5">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-citrus" />
                      <span className="text-paper/80">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-8 border-t border-paper/20 pt-5">
                <div className="flex items-center justify-between gap-4">
                  <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper/55">Due today</span>
                  <span className="font-display text-3xl leading-none text-paper">{plan.price}</span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-4 text-xs text-paper/50">
                  <span>Renews monthly</span>
                  <span>{plan.price}/month</span>
                </div>
              </div>

              <div className="mt-6 space-y-2 text-xs leading-5 text-paper/55">
                <p>Cancel anytime before your next renewal.</p>
                <p>14-day money-back guarantee.</p>
                <p>Taxes are not included in the displayed price.</p>
              </div>
            </div>
          </aside>

          <div>
            {status === 'success' && receipt ? (
              <div
                className="rounded-3xl border border-ink/10 bg-bone p-6 shadow-[0_30px_90px_-40px_rgba(23,37,31,0.4)] sm:p-8 lg:p-10"
                aria-live="polite"
              >
                <p className="eyebrow">Payment complete</p>
                <h2 className="mt-4 font-display text-[clamp(2.5rem,4vw,4.5rem)] leading-[0.95] tracking-[-0.05em] text-ink">
                  You’re all set.
                </h2>
                <p className="mt-4 max-w-xl text-ink/60">
                  Your {receipt.plan} plan is active. Download the receipt for your records.
                </p>

                <div className="mt-8 grid gap-5 border-y border-ink/15 py-6 sm:grid-cols-2">
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Receipt</p>
                    <p className="mt-2 font-mono text-sm text-ink">{receipt.reference}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Amount</p>
                    <p className="mt-2 text-ink">{receipt.amount}/month</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Billing email</p>
                    <p className="mt-2 break-all text-ink">{receipt.email}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Status</p>
                    <p className="mt-2 text-forest">Active</p>
                  </div>
                </div>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <button type="button" onClick={downloadReceipt} className="btn-primary">
                    Download receipt
                    <span aria-hidden="true">↓</span>
                  </button>
                  <Link to="/book" className="btn-secondary">
                    Book onboarding
                  </Link>
                  <Link to={`/pricing?plan=${plan.name.toLowerCase()}`} className="btn-secondary">
                    Back to pricing
                  </Link>
                </div>
              </div>
            ) : (
              <form
                className="rounded-3xl border border-ink/10 bg-bone p-6 shadow-[0_30px_90px_-40px_rgba(23,37,31,0.4)] sm:p-8 lg:p-10"
                onSubmit={handleSubmit}
                noValidate
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="eyebrow">Customer</p>
                    <p className="mt-2 max-w-md text-sm leading-6 text-ink/60">
                      Where should we send the receipt and onboarding details?
                    </p>
                  </div>
                  <div className="border-t border-ink/10 pt-4 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0 sm:text-right">
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Selected plan</p>
                    <p className="mt-1 text-sm text-ink">
                      {plan.name} · {plan.price}/month
                    </p>
                  </div>
                </div>

                <div className="mt-8 grid gap-7">
                  <Field id="email" label="Work email" error={errors.email}>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={form.email}
                      onChange={(event) => updateField('email', event.target.value)}
                      className={fieldClass(Boolean(errors.email))}
                      placeholder="amina@practice.com"
                      autoComplete="email"
                      aria-invalid={Boolean(errors.email)}
                      aria-describedby={errors.email ? 'email-error' : undefined}
                    />
                  </Field>

                  <Field id="cardName" label="Cardholder name" error={errors.cardName}>
                    <input
                      id="cardName"
                      name="cardName"
                      type="text"
                      required
                      value={form.cardName}
                      onChange={(event) => updateField('cardName', event.target.value)}
                      className={fieldClass(Boolean(errors.cardName))}
                      placeholder="Amina Rahman"
                      autoComplete="cc-name"
                      aria-invalid={Boolean(errors.cardName)}
                      aria-describedby={errors.cardName ? 'cardName-error' : undefined}
                    />
                  </Field>

                  <div className="grid gap-7 sm:grid-cols-[1.4fr_0.6fr_0.4fr]">
                    <Field id="cardNumber" label="Card number" error={errors.cardNumber}>
                      <input
                        id="cardNumber"
                        name="cardNumber"
                        type="text"
                        inputMode="numeric"
                        required
                        maxLength={19}
                        value={form.cardNumber}
                        onChange={(event) => updateField('cardNumber', formatCardNumber(event.target.value))}
                        className={fieldClass(Boolean(errors.cardNumber))}
                        placeholder="4242 4242 4242 4242"
                        autoComplete="cc-number"
                        aria-invalid={Boolean(errors.cardNumber)}
                        aria-describedby={errors.cardNumber ? 'cardNumber-error' : undefined}
                      />
                    </Field>

                    <Field id="expiry" label="Expiry" error={errors.expiry}>
                      <input
                        id="expiry"
                        name="expiry"
                        type="text"
                        inputMode="numeric"
                        required
                        maxLength={5}
                        value={form.expiry}
                        onChange={(event) => updateField('expiry', formatExpiry(event.target.value))}
                        className={fieldClass(Boolean(errors.expiry))}
                        placeholder="MM/YY"
                        autoComplete="cc-exp"
                        aria-invalid={Boolean(errors.expiry)}
                        aria-describedby={errors.expiry ? 'expiry-error' : undefined}
                      />
                    </Field>

                    <Field id="cvc" label="CVC" error={errors.cvc}>
                      <input
                        id="cvc"
                        name="cvc"
                        type="text"
                        inputMode="numeric"
                        required
                        maxLength={4}
                        value={form.cvc}
                        onChange={(event) => updateField('cvc', event.target.value.replace(/\D/g, '').slice(0, 4))}
                        className={fieldClass(Boolean(errors.cvc))}
                        placeholder="123"
                        autoComplete="cc-csc"
                        aria-invalid={Boolean(errors.cvc)}
                        aria-describedby={errors.cvc ? 'cvc-error' : undefined}
                      />
                    </Field>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={status === 'processing'}
                  className="mt-8 inline-flex w-full items-center justify-center gap-2 bg-forest px-6 py-4 font-mono text-[0.7rem] font-medium uppercase tracking-[0.14em] text-paper shadow-[0_18px_40px_-18px_rgba(28,75,58,0.7)] transition hover:bg-ink focus:outline-none focus:ring-2 focus:ring-clay focus:ring-offset-2 focus:ring-offset-bone disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {status === 'processing' ? 'Processing…' : `Pay ${plan.price}`}
                  {status === 'idle' && <span aria-hidden="true">↗</span>}
                </button>

                <div className="mt-6 grid gap-2 border-t border-ink/10 pt-5 text-xs leading-5 text-ink/55 sm:grid-cols-2">
                  <p>Recurring billing: {plan.price}/month</p>
                  <p>Cancel anytime before renewal</p>
                  <p>14-day money-back guarantee</p>
                  <a
                    href="mailto:support@otheryn.com"
                    className="border-b border-ink/20 text-ink transition hover:border-ink"
                  >
                    Support: support@otheryn.com
                  </a>
                </div>

                <div className="mt-5 flex justify-end">
                  <Link to={`/pricing?plan=${plan.name.toLowerCase()}`} className="link-arrow shrink-0">
                    Back to pricing
                    <span aria-hidden="true">↗</span>
                  </Link>
                </div>
              </form>
            )}
          </div>
        </div>
      </section>
    </>
  );
}