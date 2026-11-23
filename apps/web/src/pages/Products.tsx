import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';
import { disabledHintProps } from '../lib/disabledHint';
import { products } from '../data';
import { isProductEnabled, productAccessLabel } from '../lib/productAccess';

export default function Products() {
  return (
    <>
      <PageIntro
        index="03"
        eyebrow="The product family"
        title={<>Specialty products. <span className="italic text-forest">One foundation.</span></>}
      >
        Otheryn is the parent platform. Specialty products are built on one accountable foundation —
        starting with healthcare and expanding to other industries over time.
      </PageIntro>

      {/* Parent platform note */}
      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container grid gap-8 rounded-3xl border border-white/10 bg-forest p-7 text-paper shadow-[0_30px_80px_-30px_rgba(0,0,0,0.45)] sm:p-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <p className="eyebrow flex items-center gap-3 text-paper/60">
              <span className="h-px w-8 bg-citrus" />
              The parent platform
            </p>
            <h2 className="mt-4 max-w-2xl font-display text-[clamp(2.2rem,4vw,3.6rem)] leading-[0.95] tracking-[-0.045em] text-paper">
              One accountable layer. Many products.
            </h2>
            <p className="mt-4 max-w-xl text-paper/70">
              Products share the same identity, policy, execution and audit foundation, so each new
              specialty inherits trust instead of rebuilding it.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
            <Link to="/platform" className="btn-secondary">
              Explore the platform
            </Link>
            <Link to="/architecture" className="btn-primary">
              See the architecture
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="mb-6 flex items-center justify-between gap-4 border-b border-ink/15 pb-4">
            <p className="eyebrow">Product directory</p>
            <span className="tag">DentalPilot AI live</span>
          </div>

          <div className="grid border-l border-t border-ink/20 md:grid-cols-2 lg:grid-cols-3">
            {products.map((product, index) => {
              const enabled = isProductEnabled(product.name);
              return (
                <article
                  key={product.name}
                  aria-disabled={!enabled}
                  {...disabledHintProps(
                    enabled ? undefined : `${product.name} is planned for a future release.`,
                  )}
                  className={`group flex min-h-64 flex-col justify-between border-b border-r border-ink/20 p-6 backdrop-blur-xl transition ${
                    enabled
                      ? 'bg-white/25 hover:bg-moss/40'
                      : 'cursor-not-allowed bg-white/10 opacity-70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em]">
                    <span className="text-ink/40">0{index + 1}</span>
                    <span className={enabled ? 'text-forest' : 'text-ink/40'}>
                      {productAccessLabel(product.name)}
                    </span>
                  </div>

                  <div className="mt-16">
                    <h2 className="font-display text-3xl leading-none tracking-[-0.035em] text-ink">{product.name}</h2>
                    <p className="mt-3 max-w-xs text-sm leading-6 text-ink/60">{product.desc}</p>
                    {enabled && (
                      <Link
                        to="/book"
                        className="mt-6 inline-flex items-center gap-2 border-b border-ink/30 pb-1 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink transition hover:border-ink hover:text-forest"
                      >
                        Book a walkthrough
                        <span aria-hidden="true">↗</span>
                      </Link>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          <div className="mt-10 flex flex-col gap-4 border-t border-ink/20 pt-8 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-ink/60">
              Building for a specialty that is not listed? The shared platform is designed to support
              the next care model.
            </p>
            <Link to="/contact" className="link-arrow shrink-0">
              Talk to the team
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}