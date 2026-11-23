import { Link } from 'react-router-dom';
import PageIntro from '../components/PageIntro';

const partnerTypes = [
  {
    label: 'Technology partners',
    title: 'Connect your system to the record.',
    desc: 'Integrate your product with the shared platform and reach practices that are already working in a connected environment.',
    items: ['EHR/EMR systems', 'Medical devices & IoT', 'Laboratory systems', 'Payment processors'],
  },
  {
    label: 'Channel partners',
    title: 'Bring Otheryn to your network.',
    desc: 'Resell, refer, or implement Otheryn for the practices and groups you already serve.',
    items: ['Healthcare consultants', 'Practice management firms', 'IT service providers', 'Industry associations'],
  },
];

export default function Partners() {
  return (
    <>
      <PageIntro
        index="11"
        eyebrow="Partnerships"
        title={<>Build the future <span className="italic text-forest">with us.</span></>}
      >
        The best healthcare infrastructure is not built alone. We work with the people who understand the systems, the rooms, and the constraints.
      </PageIntro>

      <section className="bg-transparent p-5 sm:p-8 lg:p-12">
        <div className="container spatial-surface px-6 pb-12 pt-9 sm:px-8 sm:pb-14 sm:pt-12 lg:px-[60px] lg:pb-16 lg:pt-16">
          <div className="grid border-l border-t border-ink/20 md:grid-cols-2">
            {partnerTypes.map((partner, index) => (
              <div key={partner.label} className="border-b border-r border-ink/20 bg-white/15 p-7 backdrop-blur-xl lg:p-10">
                <div className="flex items-center justify-between gap-4 font-mono text-[0.55rem] uppercase tracking-[0.14em] text-ink/40">
                  <span>0{index + 1}</span>
                  <span>{partner.label}</span>
                </div>
                <h2 className="mt-10 max-w-md font-display text-4xl leading-[0.95] tracking-[-0.04em] text-ink">
                  {partner.title}
                </h2>
                <p className="mt-5 max-w-md text-ink/60">{partner.desc}</p>
                <ul className="mt-8 grid gap-2 border-t border-ink/15 pt-5 sm:grid-cols-2">
                  {partner.items.map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-ink/65">
                      <span className="h-px w-4 shrink-0 bg-clay" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-12 flex flex-col gap-4 border-t border-ink/20 pt-8 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-ink/60">
              Have an integration, referral, or co-build idea? We would rather hear it early.
            </p>
            <Link to="/contact" className="link-arrow shrink-0">
              Contact partnerships
              <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}