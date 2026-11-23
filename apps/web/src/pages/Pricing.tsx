import { Link, useSearchParams } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { pricingPlans } from '../data';

export default function Pricing() {
  const [searchParams] = useSearchParams();
  const selectedPlan = searchParams.get('plan')?.toLowerCase();
  return (
    <>
      <PageIntro
        index="06"
        eyebrow="Commercials"
        title={<>Pricing that scales <span className="italic text-forest">with the practice.</span></>}
      >
        Straightforward plans for solo clinicians, growing groups, and multi-location organizations. No hidden platform fee.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="mb-6 flex items-center justify-between gap-4 border-b border-ink/15 pb-4">
            <p className="eyebrow">DentalPilot AI plans</p>
            <span className="tag">DentalPilot AI only</span>
          </div>

          <div className="grid border border-ink/20 lg:grid-cols-3">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`flex flex-col border-ink/20 p-7 lg:border-r lg:last:border-r-0 ${
                  plan.popular ? 'bg-ink/70 text-paper backdrop-blur-2xl' : 'bg-white/30 text-ink backdrop-blur-2xl'
                } ${selectedPlan === plan.name.toLowerCase() ? 'ring-2 ring-forest ring-offset-2 ring-offset-bone' : ''}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className={`font-mono text-[0.6rem] uppercase tracking-[0.16em] ${plan.popular ? 'text-paper/50' : 'text-ink/45'}`}>
                      {plan.name}
                    </p>
                    <p className={`mt-2 text-sm ${plan.popular ? 'text-paper/60' : 'text-ink/55'}`}>{plan.desc}</p>
                  </div>
                  {plan.popular && (
                    <span className="bg-citrus px-2 py-1 font-mono text-[0.5rem] uppercase tracking-[0.14em] text-ink">
                      Most chosen
                    </span>
                  )}
                </div>

                <div className="mt-10 flex items-baseline gap-1">
                  <span className="font-display text-6xl leading-none tracking-[-0.05em]">{plan.price}</span>
                  <span className={`font-mono text-xs ${plan.popular ? 'text-paper/45' : 'text-ink/45'}`}>{plan.period}</span>
                </div>

                <ul className={`mt-10 flex-1 space-y-3 border-t pt-6 ${plan.popular ? 'border-paper/20' : 'border-ink/15'}`}>
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm">
                      <span className={`mt-2 h-px w-4 shrink-0 ${plan.popular ? 'bg-citrus' : 'bg-clay'}`} />
                      <span className={plan.popular ? 'text-paper/70' : 'text-ink/65'}>{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  to={plan.name === 'Enterprise' ? '/contact' : `/checkout?plan=${plan.name.toLowerCase()}`}
                  className={`mt-8 inline-flex items-center justify-center gap-2 px-6 py-3.5 font-mono text-[0.65rem] font-medium uppercase tracking-[0.14em] transition ${
                    plan.popular
                      ? 'bg-citrus text-ink hover:bg-paper'
                      : 'border border-ink/30 text-ink hover:border-ink hover:bg-paper'
                  }`}
                >
                  {plan.cta}
                  <span aria-hidden="true">↗</span>
                </Link>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-col gap-4 border-t border-ink/20 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink/55">
              Every plan includes onboarding, data migration support, and security review documentation.
            </p>
            <Link to="/contact" className="link-arrow shrink-0">
              Ask a pricing question
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}