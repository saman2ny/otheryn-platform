import PageIntro from '../components/PageIntro';
import { blogPosts } from '../data';

export default function Blog() {
  const [featured, ...rest] = blogPosts;

  return (
    <>
      <PageIntro
        index="07"
        eyebrow="Field notes"
        title={<>Ideas from the <span className="italic text-forest">front line.</span></>}
      >
        Notes on building healthcare software that respects the people using it. Written from the work, not from a pitch deck.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="grid border border-ink/20 lg:grid-cols-[1.15fr_0.85fr]">
            <article className="border-b border-ink/20 bg-white/30 p-7 backdrop-blur-xl lg:border-b-0 lg:border-r lg:p-12">
              <div className="flex items-center justify-between gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                <span className="text-clay">{featured.category}</span>
                <span>{featured.date}</span>
              </div>
              <h2 className="mt-10 max-w-2xl font-display text-[clamp(2.7rem,5vw,5.2rem)] leading-[0.92] tracking-[-0.055em] text-ink">
                {featured.title}
              </h2>
              <p className="mt-6 max-w-xl text-lg leading-8 text-ink/60">{featured.excerpt}</p>
            </article>

            <div>
              {rest.map((post, index) => (
                <article key={post.title} className="border-b border-ink/20 p-7 last:border-b-0 lg:p-8">
                  <div className="flex items-center justify-between gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/45">
                    <span className="text-clay">{post.category}</span>
                    <span>0{index + 2}</span>
                  </div>
                  <h3 className="mt-6 font-display text-3xl leading-none tracking-[-0.035em] text-ink">{post.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-ink/60">{post.excerpt}</p>
                  <p className="mt-5 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/35">{post.date}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}