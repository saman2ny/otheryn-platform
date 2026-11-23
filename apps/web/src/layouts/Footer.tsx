import { Link } from 'react-router-dom';
import { footerLinks } from '../data';

const currentYear = new Date().getFullYear();

export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-ink/70 text-paper shadow-[0_-30px_80px_-40px_rgba(23,37,31,0.5)] backdrop-blur-3xl backdrop-saturate-150">
      <div className="container pb-8 pt-16 sm:pt-20">
        <div className="grid gap-12 lg:grid-cols-[1.05fr_1.95fr]">
          <div>
            <Link to="/" className="mb-6 inline-flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center bg-paper font-display text-xl leading-none text-ink">O</span>
              <span className="font-display text-xl tracking-[-0.03em] text-paper">Otheryn</span>
            </Link>
            <p className="max-w-xs text-sm leading-6 text-paper/60">
              Universal Execution &amp; Trust Infrastructure. Making every execution accountable and
              every outcome verifiable.
            </p>
            <a
              href="mailto:hello.otheryn@gmail.com"
              className="mt-6 inline-block border-b border-paper/30 pb-1 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-paper/75 transition hover:border-paper hover:text-paper"
            >
              hello.otheryn@gmail.com
            </a>
          </div>

          <div className="grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-4">
            {Object.entries(footerLinks).map(([category, links]) => (
              <div key={category}>
                <h3 className="font-mono text-[0.6rem] font-medium uppercase tracking-[0.16em] text-paper/40">
                  {category}
                </h3>
                <ul className="mt-5 space-y-3">
                  {links.map((link) => (
                    <li key={`${category}-${link.label}`}>
                      <Link
                        to={link.href}
                        className="text-sm text-paper/70 transition hover:text-paper"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 flex flex-col gap-4 border-t border-paper/20 py-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper/45">
            © {currentYear} Otheryn. All rights reserved.
          </p>
          <div className="flex gap-6">
            <Link to="/privacy" className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper/55 transition hover:text-paper">
              Privacy
            </Link>
            <Link to="/terms" className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper/55 transition hover:text-paper">
              Terms
            </Link>
            <Link to="/security" className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-paper/55 transition hover:text-paper">
              Security
            </Link>
          </div>
        </div>

        <div className="border-t border-paper/20 pt-8">
          <p className="pb-3 font-display text-[clamp(2.5rem,13vw,13rem)] leading-[0.95] tracking-[-0.05em] text-paper/10">
            Otheryn
          </p>
        </div>
      </div>
    </footer>
  );
}