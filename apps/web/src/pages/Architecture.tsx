import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import {
  capabilities,
  industries,
  statusLabel,
  UETI_NAME,
} from '../data/ueti';

const badgeClass = (status: string) =>
  status === 'live'
    ? 'bg-citrus text-ink'
    : status === 'coming-soon'
      ? 'border border-ink/25 text-ink/60'
      : 'border border-ink/20 text-ink/55';

export default function Architecture() {
  return (
    <>
      <PageIntro
        index="AX"
        eyebrow="Platform architecture"
        title={<>One accountable <span className="italic text-forest">foundation.</span></>}
      >
        How the {UETI_NAME} platform is structured — core capabilities first, industry solutions on
        top. Planned capabilities are labelled and are not yet implemented.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          {/* Root */}
          <div className="flex justify-center">
            <div className="w-full max-w-md rounded-2xl border border-white/60 bg-ink/85 p-6 text-center text-paper shadow-[0_24px_60px_-24px_rgba(23,37,31,0.5)] backdrop-blur-xl">
              <p className="font-mono text-[0.55rem] uppercase tracking-[0.16em] text-citrus">
                Universal Platform
              </p>
              <p className="mt-2 font-display text-2xl leading-none tracking-[-0.03em]">
                Otheryn
              </p>
            </div>
          </div>

          {/* Connector */}
          <div className="mx-auto h-8 w-px bg-ink/25" aria-hidden="true" />

          {/* Pillars */}
          <div className="grid gap-px overflow-hidden rounded-2xl border border-ink/20 bg-ink/10 sm:grid-cols-2 lg:grid-cols-5">
            {capabilities.map((capability) => (
              <div key={capability.id} className="flex flex-col bg-bone/70 p-5 backdrop-blur-xl">
                <div className="flex items-start justify-between gap-3">
                  <span className="font-mono text-[0.6rem] text-clay">{capability.index}</span>
                  <span
                    className={`px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] ${badgeClass(
                      capability.status,
                    )}`}
                  >
                    {statusLabel(capability.status)}
                  </span>
                </div>
                <h3 className="mt-6 font-display text-xl leading-tight tracking-[-0.02em] text-ink">
                  {capability.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-ink/60">{capability.summary}</p>
              </div>
            ))}
          </div>

          {/* Connector */}
          <div className="mx-auto h-8 w-px bg-ink/25" aria-hidden="true" />

          {/* Industry solutions */}
          <div className="rounded-2xl border border-ink/20 p-5 sm:p-6">
            <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/45">
              Industry solutions
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {industries.map((industry) => (
                <div
                  key={industry.name}
                  className="rounded-xl border border-ink/15 bg-white/30 p-5 backdrop-blur-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-2xl leading-none tracking-[-0.03em] text-ink">
                      {industry.name}
                    </h3>
                    <span
                      className={`px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] ${badgeClass(
                        industry.status,
                      )}`}
                    >
                      {statusLabel(industry.status)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-ink/60">{industry.note}</p>
                  {industry.name === 'Healthcare' && (
                    <Link
                      to="/products"
                      className="mt-4 inline-flex items-center gap-2 border-b border-ink/30 pb-1 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink transition hover:border-ink hover:text-forest"
                    >
                      View products
                      <span aria-hidden="true">↗</span>
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Legend */}
          <div className="mt-8 flex flex-col gap-3 border-t border-ink/15 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/50">
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-citrus" aria-hidden="true" /> Live
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full border border-ink/30" aria-hidden="true" /> Planned
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full border border-ink/20" aria-hidden="true" /> Coming
                Soon
              </span>
            </div>
            <p className="max-w-md text-sm text-ink/55">
              Planned capabilities are not yet implemented. The diagram shows the intended structure,
              not a claim of live functionality.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-3xl">
          <p className="eyebrow">Read more</p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link to="/platform" className="btn-primary">
              Explore the platform
              <span aria-hidden="true">↗</span>
            </Link>
            <Link to="/book" className="btn-secondary">
              Book a walkthrough
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}