import PageIntro from '../components/PageIntro';

export default function Terms() {
  return (
    <>
      <PageIntro
        index="15"
        eyebrow="Legal / Terms"
        title={<>The terms <span className="italic text-forest">of the work.</span></>}
      >
        The agreement between Otheryn and the people using the platform, written to be read rather than survived.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-4xl spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="legal-copy">
            <p className="mb-10 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/40">
              Last updated: November 2026
            </p>

            <h2>1. Acceptance of terms</h2>
            <p>
              By accessing and using Otheryn services, you accept and agree to be bound by these Terms of Service.
            </p>

            <h2>2. Use of services</h2>
            <p>
              You agree to use our services only for lawful purposes and in accordance with these Terms.
            </p>

            <h2>3. Intellectual property</h2>
            <p>
              All content and materials available through Otheryn are the property of Otheryn or its licensors.
            </p>

            <h2>4. Limitation of liability</h2>
            <p>
              Otheryn shall not be liable for any indirect, incidental, or consequential damages arising from your use of our services.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}