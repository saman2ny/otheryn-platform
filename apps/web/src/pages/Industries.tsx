import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { disabledHintProps } from '../lib/disabledHint';
import { industries } from '../data';
import { industryAccessLabel, isIndustryEnabled } from '../lib/productAccess';

export default function Industries() {
  return (
    <>
      <PageIntro
        index="05"
        eyebrow="Where it applies"
        title={<>Built for the way <span className="italic text-forest">each specialty</span> works.</>}
      >
        Clinical language, patient journeys, and operating rhythms differ by specialty. The foundation stays the same; the experience adapts.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="grid border-l border-t border-ink/20 sm:grid-cols-2 lg:grid-cols-3">
            {industries.map((industry, index) => {
              const enabled = isIndustryEnabled(industry.name);
              return (
                <article
                  key={industry.name}
                  aria-disabled={!enabled}
                  {...disabledHintProps(
                    enabled ? undefined : `${industry.name} workflows are planned for a future release.`,
                  )}
                  className={`group flex min-h-60 flex-col justify-between border-b border-r border-ink/20 p-6 backdrop-blur-xl transition ${
                    enabled
                      ? 'bg-white/25 hover:bg-moss/40'
                      : 'cursor-not-allowed bg-white/10 opacity-70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em]">
                    <span className="text-ink/40">0{index + 1}</span>
                    <span className={enabled ? 'text-forest' : 'text-ink/40'}>
                      {industryAccessLabel(industry.name)}
                    </span>
                  </div>

                  <div className="mt-12">
                    <h2 className="font-display text-4xl leading-none tracking-[-0.04em] text-ink">{industry.name}</h2>
                    <p className="mt-3 text-sm leading-6 text-ink/60">{industry.desc}</p>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="mt-10 flex flex-col gap-4 border-t border-ink/20 pt-8 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-ink/60">
              Each specialty product is being built with clinical operators, not in a vacuum.
            </p>
            <Link to="/partners" className="link-arrow shrink-0">
              Partner with us
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}