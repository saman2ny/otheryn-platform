import PageIntro from '../components/PageIntro';
import { securityFeatures } from '../data';

const certifications = ['HIPAA', 'SOC 2', 'GDPR', 'CCPA'];

export default function Security() {
  return (
    <>
      <PageIntro
        index="13"
        eyebrow="Trust & security"
        title={<>Security is the <span className="italic text-forest">product.</span></>}
      >
        Patient data is the most sensitive thing in the building. We treat it that way in the architecture, the operations, and the product experience.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="grid border-l border-t border-ink/20 sm:grid-cols-2 lg:grid-cols-3">
            {securityFeatures.map((item, index) => (
              <div key={item.title} className="border-b border-r border-ink/20 bg-white/20 p-6 backdrop-blur-xl">
                <span className="font-mono text-[0.6rem] text-clay">0{index + 1}</span>
                <h2 className="mt-10 font-display text-2xl leading-none tracking-[-0.03em] text-ink">{item.title}</h2>
                <p className="mt-3 text-sm leading-6 text-ink/60">{item.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-12 rounded-[2rem] border border-white/10 bg-forest p-7 text-paper shadow-[0_40px_100px_-30px_rgba(0,0,0,0.55)] lg:p-12">
            <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
              <div>
                <p className="eyebrow flex items-center gap-3 text-paper/60">
                  <span className="h-px w-8 bg-citrus" />
                  Compliance frameworks
                </p>
                <h2 className="mt-4 font-display text-[clamp(2.5rem,5vw,4.8rem)] leading-[0.92] tracking-[-0.05em] text-paper">
                  Controls you can show.
                </h2>
              </div>
              <p className="max-w-sm text-sm leading-6 text-paper/80">
                Documentation, audit reports, and security reviews available under NDA.
              </p>
            </div>

            <div className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-paper/15 bg-paper/15 md:grid-cols-4">
              {certifications.map((cert) => (
                <div key={cert} className="flex items-center justify-center bg-forest px-4 py-5">
                  <span className="font-display text-2xl text-paper">{cert}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}