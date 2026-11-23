import { Link } from 'react-router-dom';
import HeroShell from '../components/HeroShell';
import { products } from '../data';
import { productAccessLabel, isProductEnabled } from '../lib/productAccess';
import useSpatialTilt from '../hooks/useSpatialTilt';
import {
  capabilities,
  flowSteps,
  industries,
  principles,
  problemPoints,
  statusLabel,
  UETI_NAME,
} from '../data/ueti';

const metrics = [
  { value: '01', label: 'Accountable layer' },
  { value: '5', label: 'Core capabilities' },
  { value: '1st', label: 'Healthcare vertical' },
  { value: '24/7', label: 'Verifiable outcomes' },
];

const badgeClass = (status: string) =>
  status === 'live'
    ? 'bg-citrus text-ink'
    : status === 'coming-soon'
      ? 'border border-ink/25 text-ink/60'
      : 'border border-ink/20 text-ink/55';

export default function Home() {
  const { ref: tiltRef, handlePointerMove, handlePointerLeave } = useSpatialTilt(5);

  return (
    <>
      <HeroShell
        className="overflow-hidden bg-paper/60"
        background={
          <>
            <div className="spatial-grid pointer-events-none absolute inset-0 opacity-50" />
            <div className="pointer-events-none absolute -right-32 top-[6rem] h-[34rem] w-[34rem] rounded-full bg-citrus/15 blur-3xl" />
            <div className="pointer-events-none absolute -left-40 bottom-0 h-[28rem] w-[28rem] rounded-full bg-forest/10 blur-3xl" />
          </>
        }
      >
        <div className="grid gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="animate-fade-in-up">
            <div className="mb-6 flex items-center gap-3">
              <span className="h-px w-9 bg-clay" />
              <p className="eyebrow">Universal Execution &amp; Trust Infrastructure</p>
            </div>

            <h1 className="max-w-[55rem] font-display text-[clamp(3.2rem,7vw,7.4rem)] leading-[0.88] tracking-[-0.06em] text-ink">
              Making every execution <span className="italic text-forest">accountable.</span>
            </h1>

            <p className="mt-8 max-w-xl text-lg leading-8 text-ink/65 sm:text-xl sm:leading-9">
              {UETI_NAME} for governed actions, verifiable execution and accountable outcomes across
              organizations. Healthcare is the first vertical.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link to="/book" className="btn-primary">
                Book a walkthrough
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.7} d="M5 12h14m-5-5 5 5-5 5" />
                </svg>
              </Link>
              <Link to="/platform" className="btn-secondary">
                See the platform
              </Link>
            </div>

            <div className="mt-12 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-ink/15 pt-5">
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/50">DentalPilot AI is live</p>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/50">Human + AI oversight</p>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/50">Audit-ready by design</p>
            </div>
          </div>

          <div className="relative lg:pl-4 [perspective:1400px]">
            <div className="pointer-events-none absolute -inset-5 rounded-[2rem] border border-white/60 bg-white/20 shadow-[0_30px_80px_-30px_rgba(23,37,31,0.35)] backdrop-blur-md" />

            <div className="glass-panel absolute -left-3 top-12 z-10 hidden rounded-full px-3 py-2 font-mono text-[0.55rem] uppercase tracking-[0.16em] text-ink xl:block">
              Governed / Live
            </div>

            <div
              ref={tiltRef}
              onPointerMove={handlePointerMove}
              onPointerLeave={handlePointerLeave}
              className="spatial-card relative overflow-hidden rounded-2xl border border-white/60 bg-white/55 shadow-[0_40px_100px_-30px_rgba(23,37,31,0.5)] backdrop-blur-2xl backdrop-saturate-150"
            >
              <div className="flex items-center justify-between border-b border-ink/15 px-5 py-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 bg-clay" />
                  <span className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/70">
                    Otheryn / Today
                  </span>
                </div>
                <span className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">Fig. 01</span>
              </div>

              <div className="grid grid-cols-3 border-b border-ink/15">
                <div className="border-r border-ink/15 p-4">
                  <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">Authorized</p>
                  <p className="mt-2 font-display text-3xl leading-none text-ink">100%</p>
                  <p className="mt-1 text-[0.65rem] text-ink/45">actions</p>
                </div>
                <div className="border-r border-ink/15 p-4">
                  <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">Verified</p>
                  <p className="mt-2 font-display text-3xl leading-none text-ink">98%</p>
                  <p className="mt-1 text-[0.65rem] text-ink/45">outcomes</p>
                </div>
                <div className="p-4">
                  <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">Evidence</p>
                  <p className="mt-2 font-display text-3xl leading-none text-ink">Live</p>
                  <p className="mt-1 text-[0.65rem] text-ink/45">trail</p>
                </div>
              </div>

              <div className="p-5">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">Accountable actions</p>
                    <p className="mt-1 font-display text-2xl text-forest">Governed</p>
                  </div>
                  <span className="mb-1 bg-moss px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] text-forest">
                    On record
                  </span>
                </div>

                <div className="mt-6 flex h-32 items-end gap-2" aria-hidden="true">
                  {[38, 52, 45, 68, 58, 82, 74].map((height, index) => (
                    <div
                      key={`${height}-${index}`}
                      className={`flex-1 ${index === 6 ? 'bg-clay' : 'bg-forest/85'}`}
                      style={{ height: `${height}%` }}
                    />
                  ))}
                </div>

                <div className="mt-2 flex justify-between font-mono text-[0.5rem] uppercase tracking-[0.12em] text-ink/35">
                  <span>M</span>
                  <span>T</span>
                  <span>W</span>
                  <span>T</span>
                  <span>F</span>
                  <span>S</span>
                  <span>S</span>
                </div>
              </div>

              <div className="border-t border-ink/15 p-5">
                <div className="flex items-center justify-between border-b border-ink/15 pb-3">
                  <p className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">Next verification</p>
                  <span className="font-mono text-[0.55rem] text-ink/40">Queued</span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="grid h-9 w-9 place-items-center bg-moss font-display text-sm text-forest">AR</div>
                    <div>
                      <p className="text-sm text-ink">Outcome check</p>
                      <p className="text-[0.65rem] text-ink/50">Evidence captured</p>
                    </div>
                  </div>
                  <span className="bg-citrus px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] text-ink">
                    Verifiable
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-5 flex items-center justify-between font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">
              <span>Fig. 01 — The accountable view</span>
              <span className="hidden sm:inline">One record. Zero blind spots.</span>
            </div>
          </div>
        </div>
      </HeroShell>

      <section className="relative bg-ink/80 p-5 text-paper sm:p-8 lg:p-12">
        <div className="glass-dark grid grid-cols-2 overflow-hidden rounded-2xl md:grid-cols-4">
          {metrics.map((metric, index) => (
            <div
              key={metric.label}
              className={`bg-white/5 p-5 backdrop-blur-md sm:p-6 ${
                index > 0 ? 'md:border-l md:border-paper/15' : ''
              }`}
            >
              <p className="font-display text-4xl leading-none tracking-[-0.04em] text-paper sm:text-5xl">{metric.value}</p>
              <p className="mt-3 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-paper/50">{metric.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 1. The problem */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="w-full grid gap-14 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[0.72fr_1.28fr] lg:px-12 spatial-surface overflow-visible">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <div className="mb-6 flex items-center gap-3">
              <span className="h-px w-9 bg-clay" />
              <p className="eyebrow">The problem</p>
            </div>
            <h2 className="font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Execution is easy to start. Trust is hard to prove.
            </h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-ink/60">
              The action is rarely the hard part. Knowing whether it was authorized, actually happened,
              and produced the right outcome is where trust breaks down.
            </p>
          </div>

          <div className="border-t border-ink">
            {problemPoints.map((point, index) => (
              <article
                key={point.title}
                className="grid gap-5 border-b border-ink py-7 sm:grid-cols-[3.5rem_1fr]"
              >
                <span className="font-mono text-[0.62rem] text-clay">0{index + 1}</span>
                <div>
                  <h3 className="font-display text-3xl leading-none tracking-[-0.03em] text-ink">{point.title}</h3>
                  <p className="mt-3 max-w-xl text-sm leading-7 text-ink/60">{point.desc}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* 2. The approach */}
      <section className="bg-forest/80 p-5 text-paper sm:p-8 lg:p-12">
        <div className="w-full grid gap-10 px-5 py-20 sm:px-8 sm:py-28 lg:px-12 spatial-surface-dark">
          <div className="max-w-2xl">
            <div className="mb-6 flex items-center gap-3">
              <span className="h-px w-9 bg-citrus" />
              <p className="eyebrow text-paper/55">The approach</p>
            </div>
            <h2 className="font-display text-[clamp(2.8rem,6vw,5.6rem)] leading-[0.9] tracking-[-0.055em] text-paper">
              One accountable layer around every execution.
            </h2>
            <p className="mt-6 max-w-xl text-lg leading-8 text-paper/65">
              Otheryn governs who can act, orchestrates how work flows, captures evidence as it
              happens, and produces a verifiable record of the outcome. People, AI agents and connected
              systems all execute through the same accountable layer.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {['Govern', 'Execute', 'Verify'].map((step, index) => (
              <div key={step} className="flex items-center gap-3">
                <span className="border border-paper/25 px-4 py-2 font-mono text-[0.6rem] uppercase tracking-[0.16em] text-paper">
                  {step}
                </span>
                {index < 2 && (
                  <span className="font-mono text-[0.6rem] text-citrus" aria-hidden="true">
                    →
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Core capabilities */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <h2 className="max-w-2xl font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Core platform capabilities.
            </h2>
            <p className="max-w-md text-ink/60">
              Five capabilities that turn any action into an accountable, verifiable outcome. All are
              planned and not yet implemented.
            </p>
          </div>

          <div className="mt-10 grid border-l border-t border-ink/20 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((capability) => (
              <div key={capability.id} className="border-b border-r border-ink/20 p-6">
                <div className="flex items-start justify-between gap-3">
                  <span className="font-mono text-[0.6rem] text-clay">{capability.index}</span>
                  <span className={`px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] ${badgeClass(capability.status)}`}>
                    {statusLabel(capability.status)}
                  </span>
                </div>
                <h3 className="mt-10 font-display text-2xl leading-none tracking-[-0.03em] text-ink">{capability.title}</h3>
                <p className="mt-3 text-sm leading-6 text-ink/60">{capability.summary}</p>
              </div>
            ))}
            <div className="flex items-center border-b border-r border-ink/20 p-6">
              <Link to="/platform" className="link-arrow">
                Explore the platform
                <span aria-hidden="true">↗</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 4. How it works */}
      <section className="relative bg-citrus/80 p-5 sm:p-8 lg:p-12">
        <div className="spatial-grid pointer-events-none absolute inset-0 opacity-30" />
        <div className="glass-panel w-full rounded-3xl p-8 sm:p-12">
          <p className="eyebrow text-ink/55">How it works</p>
          <h2 className="mt-4 max-w-3xl font-display text-[clamp(2.6rem,5vw,4.8rem)] leading-[0.9] tracking-[-0.055em] text-ink">
            From authorization to a sealed record.
          </h2>
          <ol className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-ink/15 bg-ink/10 sm:grid-cols-2 lg:grid-cols-5">
            {flowSteps.map((step) => (
              <li key={step.step} className="bg-paper/80 p-5 backdrop-blur-md">
                <span className="font-mono text-[0.6rem] text-clay">{step.step}</span>
                <h3 className="mt-6 font-display text-xl leading-none tracking-[-0.02em] text-ink">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-ink/60">{step.desc}</p>
              </li>
            ))}
          </ol>
          <p className="mt-6 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
            Planned platform flow — not yet implemented.
          </p>
        </div>
      </section>

      {/* 5. Industry solutions */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container grid gap-14 lg:grid-cols-[0.7fr_1.3fr] spatial-surface overflow-visible px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <div className="mb-6 flex items-center gap-3">
              <span className="h-px w-9 bg-clay" />
              <p className="eyebrow">Industry solutions</p>
            </div>
            <h2 className="font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Built once. Applied per industry.
            </h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-ink/60">
              The accountable layer stays constant. The workflows, language and decisions adapt to each
              industry.
            </p>
            <Link to="/architecture" className="link-arrow mt-8">
              See the architecture
              <span aria-hidden="true">↗</span>
            </Link>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {industries.map((industry) => (
              <div key={industry.name} className="rounded-2xl border border-ink/20 bg-white/25 p-6 backdrop-blur-xl">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-display text-2xl leading-none tracking-[-0.03em] text-ink">{industry.name}</h3>
                  <span className={`px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] ${badgeClass(industry.status)}`}>
                    {statusLabel(industry.status)}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-ink/60">{industry.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. Products */}
      <section className="bg-ink/80 p-5 text-paper sm:p-8 lg:p-12">
        <div className="container spatial-surface-dark px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <h2 className="max-w-2xl font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-paper">
              Specialty products on one accountable foundation.
            </h2>
            <Link
              to="/products"
              className="inline-flex items-center gap-2 border-b border-paper/40 pb-1 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-paper transition hover:border-paper"
            >
              All products
              <span aria-hidden="true">↗</span>
            </Link>
          </div>

          <div className="mt-10 grid border-l border-t border-paper/20 sm:grid-cols-2 lg:grid-cols-3">
            {products.slice(0, 6).map((product, index) => {
              const enabled = isProductEnabled(product.name);
              return (
                <div
                  key={product.name}
                  className={`flex min-h-32 flex-col justify-between border-b border-r border-paper/20 p-5 ${
                    enabled ? 'bg-white/5' : 'bg-white/5 opacity-60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 font-mono text-[0.55rem] uppercase tracking-[0.12em] text-paper/45">
                    <span>0{index + 1}</span>
                    <span className={enabled ? 'text-citrus' : 'text-paper/30'}>
                      {productAccessLabel(product.name)}
                    </span>
                  </div>
                  <div className="mt-8">
                    <h3 className="font-display text-xl leading-none tracking-[-0.02em] text-paper">{product.name}</h3>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 7. Trust & governance */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <h2 className="max-w-2xl font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Every action authorized. Every outcome verifiable.
            </h2>
            <Link to="/security" className="link-arrow shrink-0">
              Trust &amp; security
              <span aria-hidden="true">↗</span>
            </Link>
          </div>

          <div className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-ink/20 bg-ink/10 sm:grid-cols-2 lg:grid-cols-4">
            {principles.map((principle, index) => (
              <div key={principle.title} className="bg-bone/70 p-6 backdrop-blur-xl">
                <span className="font-mono text-[0.6rem] text-clay">0{index + 1}</span>
                <h3 className="mt-10 font-display text-xl leading-tight tracking-[-0.02em] text-ink">{principle.title}</h3>
                <p className="mt-3 text-sm leading-6 text-ink/60">{principle.desc}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-sm text-ink/50">
            Design principles for the platform. No compliance or certification claims are made here.
          </p>
        </div>
      </section>

      {/* 8. Call to action */}
      <section className="relative overflow-hidden bg-citrus/80 p-5 sm:p-8 lg:p-12">
        <div className="spatial-grid pointer-events-none absolute inset-0 opacity-30" />
        <div className="glass-panel w-full rounded-3xl p-8 sm:p-12">
          <div className="grid gap-9 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <p className="eyebrow text-ink/55">Next step</p>
              <h2 className="mt-4 max-w-4xl font-display text-[clamp(3rem,6.5vw,6.5rem)] leading-[0.88] tracking-[-0.06em] text-ink">
                See accountability in practice.
              </h2>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
              <Link to="/book" className="btn-primary">
                Book a walkthrough
                <span aria-hidden="true">↗</span>
              </Link>
              <Link to="/contact" className="btn-secondary">
                Talk to the team
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}