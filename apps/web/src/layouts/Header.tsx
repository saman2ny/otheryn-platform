import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { navItems } from '../data';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8);
    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4 sm:px-6">
        <nav
          aria-label="Primary navigation"
          className={`mx-auto flex h-16 max-w-[90rem] items-center justify-between gap-6 rounded-2xl border px-4 backdrop-blur-2xl backdrop-saturate-150 transition-all duration-300 sm:px-6 ${
            scrolled
              ? 'border-white/70 bg-white/40 shadow-[0_20px_60px_-24px_rgba(23,37,31,0.35)]'
              : 'border-white/50 bg-white/25 shadow-[0_12px_40px_-24px_rgba(23,37,31,0.25)]'
          }`}
        >
          <Link to="/" className="flex shrink-0 items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-ink font-display text-xl leading-none text-paper shadow-[0_8px_20px_-8px_rgba(23,37,31,0.55)]">
              O
            </span>
            <span className="font-display text-xl tracking-[-0.03em] text-ink">Otheryn</span>
            <span className="mb-4 font-mono text-[0.5rem] text-ink/45">®</span>
          </Link>

          <div className="hidden items-center gap-6 lg:flex">
            {navItems.map((item) => {
              const active = location.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`relative py-2 font-mono text-[0.6rem] font-medium uppercase tracking-[0.14em] transition ${
                    active ? 'text-ink' : 'text-ink/55 hover:text-ink'
                  }`}
                >
                  {item.label}
                  {active && <span className="absolute inset-x-0 -bottom-0.5 h-px bg-clay" />}
                </Link>
              );
            })}
          </div>

          <div className="hidden items-center gap-3 lg:flex">
            <Link to="/book" className="btn-primary">
              Book a walkthrough
              <span aria-hidden="true">↗</span>
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileMenuOpen((open) => !open)}
            className="flex items-center gap-3 lg:hidden"
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
          >
            <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/60">
              {mobileMenuOpen ? 'Close' : 'Menu'}
            </span>
            <span className="flex w-5 flex-col gap-1.5" aria-hidden="true">
              <span
                className={`h-px w-full bg-ink transition-transform duration-200 ${
                  mobileMenuOpen ? 'translate-y-[3px] rotate-45' : ''
                }`}
              />
              <span
                className={`h-px w-full bg-ink transition-transform duration-200 ${
                  mobileMenuOpen ? '-translate-y-[3px] -rotate-45' : ''
                }`}
              />
            </span>
          </button>
        </nav>
      </header>

      {createPortal(
        <div
          id="mobile-navigation"
          className={`fixed inset-x-4 bottom-4 top-20 z-40 overflow-y-auto rounded-2xl border border-white/60 bg-white/40 shadow-[0_30px_90px_-20px_rgba(23,37,31,0.45)] backdrop-blur-3xl backdrop-saturate-150 transition-all duration-200 lg:hidden ${
            mobileMenuOpen ? 'visible opacity-100' : 'invisible opacity-0'
          }`}
        >
          <nav className="flex min-h-full flex-col p-6">
            <div className="flex items-center justify-between border-b border-ink/15 pb-4">
              <p className="eyebrow">Navigate</p>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ink/40">Otheryn</p>
            </div>

            {navItems.map((item, index) => (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="group flex items-center justify-between border-b border-ink/15 py-5"
              >
                <span className="font-display text-4xl tracking-[-0.04em] text-ink transition group-hover:text-forest">
                  {item.label}
                </span>
                <span className="font-mono text-[0.6rem] text-ink/40">0{index + 1}</span>
              </Link>
            ))}

            <div className="mt-auto grid gap-3 pt-10">
              <Link
                to="/book"
                onClick={() => setMobileMenuOpen(false)}
                className="btn-primary w-full"
              >
                Book a walkthrough
                <span aria-hidden="true">↗</span>
              </Link>
              <Link
                to="/contact"
                onClick={() => setMobileMenuOpen(false)}
                className="btn-secondary w-full"
              >
                Contact the team
              </Link>
            </div>
          </nav>
        </div>,
        document.body,
      )}
    </>
  );
}