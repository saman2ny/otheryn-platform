import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';

const heading = 'mb-6 text-3xl leading-[1.2] tracking-[-0.02em] text-ink [text-wrap:balance]';
const body = 'mb-6 max-w-[44rem] text-lg leading-[1.65] text-ink/65 [overflow-wrap:break-word] [text-wrap:pretty] last:mb-0';

export default function Privacy() {
  return (
    <>
      <PageIntro
        index="14"
        eyebrow="Legal / Privacy"
        title={<>Your data, <span className="italic text-forest">handled carefully.</span></>}
      >
        This policy explains what we collect, why we collect it, and the controls you have over your information.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-4xl spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <p className="mb-12 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/40 sm:mb-14">
            Last updated: November 2026
          </p>

          <div>
            <h2 className={`mt-0 ${heading}`}>1. Information we collect</h2>
            <p className={body}>
              We collect information you provide directly to us, such as when you create an account, contact us, or use our services. We also collect limited technical information required to operate and secure the platform.
            </p>

            <h2 className={`mt-12 ${heading}`}>2. How we use your information</h2>
            <p className={body}>
              We use your information to provide, maintain, and improve our services, communicate with you, meet legal obligations, and protect the integrity of the platform.
            </p>

            <h2 className={`mt-12 ${heading}`}>3. Data security</h2>
            <p className={body}>
              We implement industry-standard security measures to protect your data, including encryption at rest and in transit, access controls, audit logging, and regular security assessments.
            </p>

            <h2 className={`mt-12 ${heading}`}>4. Your rights</h2>
            <p className={body}>
              You have the right to access, correct, or delete your personal information. Contact us at{' '}
              <a href="mailto:privacy@otheryn.com" className="border-b border-ink/30 text-ink transition hover:border-ink">
                privacy@otheryn.com
              </a>
              .
            </p>

            <p className={body}>
              Our use of cookies and similar technologies is described in our{' '}
              <Link to="/cookie-policy" className="border-b border-ink/30 text-ink transition hover:border-ink">
                Cookie Policy
              </Link>
              .
            </p>
          </div>
        </div>
      </section>
    </>
  );
}