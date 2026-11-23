import PageIntro from '../components/PageIntro';

export default function CookiePolicy() {
  return (
    <>
      <PageIntro
        index="17"
        eyebrow="Legal / Cookies"
        title={<>Cookies, <span className="italic text-forest">with controls.</span></>}
      >
        This policy explains how Otheryn uses cookies and similar technologies, and how you can control them.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container max-w-4xl spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="legal-copy">
            <p className="mb-10 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/40">
              Last updated: November 2026
            </p>

            <h2>1. What are cookies?</h2>
            <p>
              Cookies are small text files stored on your device when you visit a website. They help the site remember actions and preferences, keep sessions secure, and understand how the site is used.
            </p>

            <h2>2. Cookies we use</h2>
            <p>
              <strong>Strictly necessary cookies</strong> keep the site working, including security, session handling, and load balancing. These cannot be disabled through the site.
            </p>
            <p>
              <strong>Analytics cookies</strong> help us understand which pages are useful and where visitors get stuck. They are used in aggregate and are not used to identify you personally.
            </p>
            <p>
              <strong>Product cookies</strong> remember preferences such as your selected specialty or whether you have dismissed a notice.
            </p>

            <h2>3. Your choices</h2>
            <p>
              You can block or delete cookies in your browser settings. Blocking strictly necessary cookies may prevent parts of the site from working correctly. You can also opt out of analytics cookies at any time.
            </p>

            <h2>4. Changes to this policy</h2>
            <p>
              We may update this policy as the product and our use of cookies evolve. The latest version will always be available on this page.
            </p>

            <h2>5. Contact</h2>
            <p>
              Questions about cookies can be sent to{' '}
              <a href="mailto:privacy@otheryn.com" className="border-b border-ink/30 text-ink transition hover:border-ink">
                privacy@otheryn.com
              </a>
              .
            </p>
          </div>
        </div>
      </section>
    </>
  );
}