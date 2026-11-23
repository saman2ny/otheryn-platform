import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { capabilities, statusLabel, UETI_NAME } from '../data/ueti';

const badgeClass =
  'border border-ink/20 px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] text-ink/55';

export default function Platform() {
  return (
    <>
      <PageIntro
        index="02"
        eyebrow="The platform"
        title={<>The system behind <span className="italic text-forest">accountable execution.</span></>}
      >
        One shared layer for identity, policy, orchestration, evidence and audit. Specialty products
        and industry solutions build on top without rebuilding the basics.
      </PageIntro>

      {/* Relationship overview */}
      <section className="bg-ink/80 p-5 text-paper sm:p-8 lg:p-12">
        <div className="w-full spatial-surface-dark px-5 py-16 sm:px-8 sm:py-24 lg:px-12">
          <div className="max-w-2xl">
            <p className="eyebrow text-paper/50">How the capabilities relate</p>
            <h2 className="mt-4 font-display text-[clamp(2.6rem,5vw,4.8rem)] leading-[0.92] tracking-[-0.05em] text-paper">
              Govern. Execute. Prove.
            </h2>
            <p className="mt-6 max-w-xl text-lg leading-8 text-paper/65">
              Each capability feeds the next. Authorization and policy decide what may run; execution
              carries the work; evidence and audit make the outcome reviewable.
            </p>
          </div>

          <div className="mt-10 flex flex-wrap items-center gap-2">
            {capabilities.map((capability, index) => (
              <div key={capability.id} className="flex items-center gap-2">
                <span className="border border-paper/20 px-3 py-2 font-mono text-[0.55rem] uppercase tracking-[0.12em] text-paper/80">
                  {capability.title}
                </span>
                {index < capabilities.length - 1 && (
                  <span className="font-mono text-[0.6rem] text-citrus" aria-hidden="true">
                    →
                  </span>
                )}
              </div>
            ))}
          </div>
          <p className="mt-6 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-paper/40">
            All capabilities shown are planned and not yet implemented.
          </p>
        </div>
      </section>

      {/* Capability detail */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="border-t border-ink">
            {capabilities.map((capability) => (
              <div
                key={capability.id}
                className="grid gap-6 border-b border-ink py-8 lg:grid-cols-[0.6fr_1.4fr] lg:gap-10"
              >
                <div className="flex items-start gap-5">
                  <span className="font-mono text-[0.62rem] text-clay">{capability.index}</span>
                  <div>
                    <h2 className="font-display text-3xl leading-none tracking-[-0.035em] text-ink">
                      {capability.title}
                    </h2>
                    <span className={`mt-3 inline-block ${badgeClass}`}>{statusLabel(capability.status)}</span>
                  </div>
                </div>
                <div>
                  <p className="max-w-2xl text-lg leading-8 text-ink/70">{capability.summary}</p>
                  <p className="mt-4 max-w-2xl text-base leading-7 text-ink/55">{capability.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Closing */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-3xl spatial-surface px-6 py-12 sm:px-8 sm:py-16">
          <p className="eyebrow">Built on one foundation</p>
          <h2 className="mt-4 font-display text-[clamp(2.4rem,4.6vw,4.4rem)] leading-[0.92] tracking-[-0.05em] text-ink">
            Healthcare is the first vertical.
          </h2>
          <p className="mt-6 text-lg leading-8 text-ink/60">
            {UETI_NAME} is designed to be industry-agnostic. DentalPilot AI is the first enabled
            product built on this foundation; additional industries are planned.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/architecture" className="btn-primary">
              See the architecture
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