import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';

const pillars = [
  {
    title: 'Authorization',
    desc: 'Before an action runs, there is an explicit, checkable decision about who or what may act.',
  },
  {
    title: 'Evidence',
    desc: 'Proof is captured while the work happens, not reconstructed after something goes wrong.',
  },
  {
    title: 'Accountability',
    desc: 'Every action and outcome stays tied to an owner and a reviewable record.',
  },
];

export default function About() {
  return (
    <>
      <PageIntro
        index="01"
        eyebrow="Why Otheryn"
        title={<>Software that <span className="italic text-forest">shows its work.</span></>}
      >
        Otheryn exists to close the gap between an action being taken and its outcome being proven. We
        build accountable execution infrastructure, starting with healthcare.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="w-full grid gap-14 lg:grid-cols-[0.9fr_1.1fr] spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div>
            <p className="eyebrow">Our mission</p>
            <h2 className="mt-4 font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              The missing layer is accountability.
            </h2>
            <p className="mt-6 max-w-xl text-lg leading-8 text-ink/60">
              Every day, organizations delegate real actions to people, AI agents and connected
              systems. The action is rarely the hard part. Proving that it was authorized, that it
              happened, and that it produced the right outcome is.
            </p>
            <p className="mt-4 max-w-xl text-lg leading-8 text-ink/60">
              Otheryn is the infrastructure layer that makes those three things — authorization,
              evidence and accountability — part of how work runs, not an afterthought.
            </p>
          </div>

          <div className="border-t border-ink">
            {pillars.map((pillar, index) => (
              <div key={pillar.title} className="grid gap-3 border-b border-ink py-6 sm:grid-cols-[3rem_1fr]">
                <span className="font-mono text-[0.62rem] text-clay">0{index + 1}</span>
                <div>
                  <h3 className="font-display text-2xl leading-none tracking-[-0.03em] text-ink">{pillar.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-ink/60">{pillar.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-ink/15 bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="w-full grid gap-14 lg:grid-cols-[0.8fr_1.2fr] spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div>
            <p className="eyebrow">The gap</p>
            <h2 className="mt-4 font-display text-[clamp(2.6rem,4.6vw,4.6rem)] leading-[0.92] tracking-[-0.05em] text-ink">
              Executing an action is not the same as verifying it.
            </h2>
          </div>
          <div className="space-y-5 text-lg leading-8 text-ink/65">
            <p>
              Most systems record that an action was requested. Far fewer can show that it was
              authorized, that it completed, and that the intended outcome actually occurred.
            </p>
            <p>
              That gap is where trust erodes — between teams, between organizations, and between
              people and the AI agents now doing work on their behalf.
            </p>
            <p>
              Otheryn is designed to close it: one accountable layer that governs, executes, captures
              evidence and verifies outcomes across the systems an organization already runs.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-forest/80 p-5 text-paper sm:p-8 lg:p-12">
        <div className="w-full grid gap-10 px-5 py-20 sm:px-8 sm:py-28 lg:grid-cols-[0.85fr_1.15fr] lg:px-12 spatial-surface-dark">
          <div>
            <div className="mb-6 flex items-center gap-3">
              <span className="h-px w-9 bg-citrus" />
              <p className="eyebrow text-paper/55">The long view</p>
            </div>
            <h2 className="font-display text-[clamp(2.8rem,5.5vw,5.4rem)] leading-[0.9] tracking-[-0.055em] text-paper">
              Cross-industry by design. Healthcare first.
            </h2>
          </div>
          <div className="space-y-5 text-lg leading-8 text-paper/70">
            <p>
              Accountability is not specific to one sector. Any organization that delegates actions to
              people and software needs to prove what happened.
            </p>
            <p>
              We start with healthcare — a domain where the cost of an unverified outcome is high —
              and expand the same accountable foundation to other industries over time.
            </p>
            <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-paper/50">
              DentalPilot AI is the first enabled product. Additional industries are planned.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t border-ink/15 bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="w-full grid gap-8 p-6 sm:p-8 lg:grid-cols-12 lg:items-end lg:p-12 spatial-surface">
          <blockquote className="max-w-5xl font-display text-[clamp(2.4rem,5vw,5.2rem)] leading-[0.94] tracking-[-0.055em] text-ink [text-wrap:pretty] lg:col-span-9">
            “The best infrastructure is the kind that lets you trust the work without having to
            rebuild the proof yourself.”
          </blockquote>
          <div className="lg:col-span-3 lg:border-l lg:border-ink/15 lg:pb-2 lg:pl-6">
            <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-ink/45">
              Otheryn / Operating principle
            </p>
            <Link to="/platform" className="link-arrow mt-4">
              See the platform
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}