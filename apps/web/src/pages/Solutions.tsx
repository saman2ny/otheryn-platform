import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { solutions } from '../data';

export default function Solutions() {
  return (
    <>
      <PageIntro
        index="04"
        eyebrow="What changes on Monday"
        title={<>Solutions for the work <span className="italic text-forest">between</span> appointments.</>}
      >
        The practice does not run on one big idea. It runs on a hundred small handoffs. Otheryn connects the ones that matter most.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container grid gap-14 lg:grid-cols-[0.7fr_1.3fr] spatial-surface overflow-visible px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <p className="eyebrow">The operating map</p>
            <h2 className="mt-4 font-display text-[clamp(2.8rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
              Less chasing. More clarity.
            </h2>
            <p className="mt-6 max-w-md text-lg leading-8 text-ink/60">
              From the front desk to the treatment room, the same record follows the patient without the team having to stitch it together.
            </p>
            <Link to="/book" className="link-arrow mt-8">
              See it in your workflow
              <span aria-hidden="true">↗</span>
            </Link>
          </div>

          <div className="border-t border-ink">
            {solutions.map((solution, index) => (
              <div key={solution.title} className="grid gap-6 border-b border-ink py-8 lg:grid-cols-[0.8fr_1.2fr]">
                <div className="flex gap-5">
                  <span className="font-mono text-[0.62rem] text-clay">0{index + 1}</span>
                  <h2 className="font-display text-3xl leading-none tracking-[-0.035em] text-ink">{solution.title}</h2>
                </div>

                <div>
                  <p className="text-ink/60">{solution.desc}</p>
                  <ul className="mt-5 grid gap-2 sm:grid-cols-2">
                    {solution.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-sm text-ink/70">
                        <span className="h-px w-4 shrink-0 bg-clay" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}