import PageIntro from '../components/PageIntro';

const roles = [
  'Senior Full Stack Engineer',
  'AI/ML Engineer',
  'Product Designer',
  'Healthcare Solutions Architect',
];

export default function Careers() {
  return (
    <>
      <PageIntro
        index="08"
        eyebrow="Careers"
        title={<>Do the best work <span className="italic text-forest">with people who care.</span></>}
      >
        We are a small, distributed team building software for people who work in healthcare. High trust, low noise, real ownership.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container grid gap-14 lg:grid-cols-[0.8fr_1.2fr] spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div>
            <p className="eyebrow">Open roles</p>
            <h2 className="mt-4 font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Come build the day.
            </h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-ink/60">
              We care about craft, clear thinking, and the patient on the other side of the workflow. If that sounds like your kind of team, we should talk.
            </p>
            <a href="mailto:careers@otheryn.com" className="btn-primary mt-8">
              Send your work
              <span aria-hidden="true">↗</span>
            </a>
          </div>

          <div className="border-t border-ink">
            {roles.map((role, index) => (
              <a
                key={role}
                href="mailto:careers@otheryn.com"
                className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-4 border-b border-ink py-6"
              >
                <span className="font-mono text-[0.62rem] text-clay">0{index + 1}</span>
                <span className="font-display text-2xl leading-none tracking-[-0.03em] text-ink transition group-hover:text-forest sm:text-3xl">
                  {role}
                </span>
                <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/35 transition group-hover:text-ink">
                  Apply ↗
                </span>
              </a>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}