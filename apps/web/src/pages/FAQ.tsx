import { useState } from 'react';
import PageIntro from '../components/PageIntro';
import { faqs } from '../data';

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <>
      <PageIntro
        index="10"
        eyebrow="Questions"
        title={<>The things <span className="italic text-forest">worth asking.</span></>}
      >
        Straight answers about the platform, security, implementation, and what it is like to work with us.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-5xl spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="border-t border-ink">
            {faqs.map((faq, index) => {
              const open = openIndex === index;
              return (
                <div key={faq.q} className="border-b border-ink">
                  <button
                    type="button"
                    onClick={() => setOpenIndex(open ? null : index)}
                    aria-expanded={open}
                    className="flex w-full items-center justify-between gap-6 py-6 text-left"
                  >
                    <span className="flex items-start gap-5">
                      <span className="mt-1 font-mono text-[0.6rem] text-clay">0{index + 1}</span>
                      <span className="font-display text-2xl leading-tight tracking-[-0.025em] text-ink sm:text-3xl">
                        {faq.q}
                      </span>
                    </span>
                    <span className={`text-2xl text-ink/50 transition-transform ${open ? 'rotate-45' : ''}`} aria-hidden="true">
                      +
                    </span>
                  </button>
                  {open && (
                    <p className="max-w-3xl pb-7 pl-9 text-ink/60 sm:pl-10">{faq.a}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </>
  );
}