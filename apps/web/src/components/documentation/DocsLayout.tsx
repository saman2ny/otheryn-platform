import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { DOC_ARTICLES, DOC_NAV, getAdjacentDocs, getDocArticle } from '../../data/documentation';
import type { DocArticle, DocBlock } from '../../data/documentation';

function CodeBlock({ block }: { block: Extract<DocBlock, { type: 'code' }> }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(block.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="my-6 overflow-hidden rounded-2xl border border-white/50 bg-ink/[0.92] shadow-[0_20px_60px_-30px_rgba(23,37,31,0.55)]">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[0.55rem] uppercase tracking-[0.14em] text-paper/45">{block.language}</span>
          {block.label && <span className="text-xs text-paper/60">{block.label}</span>}
        </div>
        <button
          type="button"
          onClick={copy}
          className="rounded-lg border border-white/15 px-3 py-1.5 font-mono text-[0.55rem] uppercase tracking-[0.12em] text-paper/70 transition hover:border-white/30 hover:text-paper"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-[0.8rem] leading-6 text-paper/85"><code>{block.code}</code></pre>
    </div>
  );
}

function DocBlocks({ blocks }: { blocks: DocBlock[] }) {
  return (
    <div>
      {blocks.map((block, index) => {
        if (block.type === 'paragraph') {
          return <p key={index} className="mb-5 text-base leading-8 text-ink/72">{block.text}</p>;
        }
        if (block.type === 'heading') {
          return (
            <h2 key={block.id} id={block.id} className="scroll-mt-28 mb-4 mt-10 font-display text-3xl tracking-[-0.03em] text-ink first:mt-0">
              {block.text}
            </h2>
          );
        }
        if (block.type === 'list') {
          return (
            <ul key={index} className="mb-6 space-y-3 pl-5 text-base leading-7 text-ink/72">
              {block.items.map((item) => <li key={item} className="list-disc marker:text-clay">{item}</li>)}
            </ul>
          );
        }
        if (block.type === 'code') {
          return <CodeBlock key={index} block={block} />;
        }
        if (block.type === 'callout') {
          const tone = {
            info: 'border-forest/20 bg-forest/[0.06] text-forest',
            warning: 'border-clay/25 bg-clay/[0.06] text-clay',
            planned: 'border-ink/20 bg-ink/[0.04] text-ink/75',
          }[block.tone];
          return (
            <div key={index} className={`my-6 rounded-2xl border px-5 py-4 ${tone}`}>
              <p className="font-mono text-[0.58rem] uppercase tracking-[0.14em]">{block.title}</p>
              <p className="mt-2 text-sm leading-7 text-ink/72">{block.text}</p>
            </div>
          );
        }
        if (block.type === 'table') {
          return (
            <div key={index} className="my-6 overflow-x-auto rounded-2xl border border-ink/10 bg-white/35">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-ink/[0.03] text-ink/60">
                  <tr>
                    {block.columns.map((col) => (
                      <th key={col} className="px-4 py-3 font-mono text-[0.55rem] font-medium uppercase tracking-[0.12em]">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-t border-ink/10 align-top">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-4 py-3 leading-6 text-ink/72">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

function Toc({ article }: { article: DocArticle }) {
  const headings = article.blocks.filter((b): b is Extract<DocBlock, { type: 'heading' }> => b.type === 'heading');
  const [active, setActive] = useState(headings[0]?.id);
  useEffect(() => {
    const elements = headings.map((h) => document.getElementById(h.id)).filter(Boolean) as HTMLElement[];
    if (!elements.length) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible?.target.id) setActive(visible.target.id);
    }, { rootMargin: '-120px 0px -70% 0px', threshold: [0, 1] });
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [article.id, headings]);
  if (!headings.length) return null;
  return (
    <aside className="hidden xl:block">
      <div className="sticky top-28 rounded-2xl border border-white/55 bg-white/30 p-5 backdrop-blur-xl">
        <p className="font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ink/45">On this page</p>
        <ul className="mt-4 space-y-2">
          {headings.map((h) => (
            <li key={h.id}>
              <a href={`#${h.id}`} className={`block text-sm leading-6 transition ${active === h.id ? 'text-forest' : 'text-ink/55 hover:text-ink'}`}>
                {h.text}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

export default function DocsLayout({ slug }: { slug?: string }) {
  const article = getDocArticle(slug);
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const adjacent = getAdjacentDocs(article.slug);

  useEffect(() => { setMobileNavOpen(false); }, [location.pathname]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return DOC_ARTICLES.filter((doc) => {
      const haystack = [doc.title, doc.description, doc.navLabel, ...doc.blocks.flatMap((b) => {
        if (b.type === 'paragraph' || b.type === 'heading' || b.type === 'callout') return [b.text, 'title' in b ? b.title : ''];
        if (b.type === 'list') return b.items;
        if (b.type === 'table') return [...b.columns, ...b.rows.flat()];
        if (b.type === 'code') return [b.code, b.label ?? '', b.language];
        return [];
      })].join(' ').toLowerCase();
      return haystack.includes(q);
    }).slice(0, 8);
  }, [query]);

  const nav = (
    <div className="rounded-2xl border border-white/55 bg-white/30 p-4 backdrop-blur-xl">
      <div className="mb-4">
        <label className="font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ink/45" htmlFor="doc-search">Search documentation</label>
        <input
          id="doc-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search guides, APIs, operations..."
          className="mt-2 w-full rounded-xl border border-ink/10 bg-white/55 px-3 py-2.5 text-sm text-ink placeholder:text-ink/35 focus:border-forest/30 focus:outline-none focus:ring-2 focus:ring-forest/15"
        />
        {query.trim() && (
          <div className="mt-2 rounded-xl border border-ink/10 bg-bone/90 p-2">
            {results.length ? results.map((result) => (
              <Link key={result.id} to={result.path} onClick={() => setQuery('')} className="block rounded-lg px-3 py-2 text-sm text-ink/70 hover:bg-ink/[0.04] hover:text-ink">
                <div className="font-medium text-ink">{result.navLabel}</div>
                <div className="line-clamp-1 text-xs text-ink/50">{result.description}</div>
              </Link>
            )) : <div className="px-3 py-2 text-xs text-ink/45">No matching documentation.</div>}
          </div>
        )}
      </div>
      {DOC_NAV.map((group) => (
        <div key={group.title}>
          <p className="px-2 font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ink/45">{group.title}</p>
          <ul className="mt-3 space-y-1">
            {group.items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end
                  className={({ isActive }) => `block rounded-xl px-3 py-2.5 text-sm transition ${isActive ? 'bg-ink text-paper shadow-[0_10px_30px_-18px_rgba(23,37,31,0.7)]' : 'text-ink/68 hover:bg-ink/[0.04] hover:text-ink'}`}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );

  return (
    <div className="bg-paper">
      <section className="relative mt-20 border-b border-ink/15 p-5 sm:p-8 lg:p-12">
        <div className="spatial-surface p-6 sm:p-8 lg:p-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-5 flex items-center gap-3">
                <span className="font-mono text-[0.65rem] text-clay">DOCS</span>
                <span className="h-px w-8 bg-ink/25" />
                <p className="eyebrow">Documentation Centre</p>
              </div>
              <h1 className="font-display text-[clamp(2.8rem,6vw,5.5rem)] leading-[0.9] tracking-[-0.055em] text-ink">
                Build with <span className="italic text-forest">clarity.</span>
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-ink/65 sm:text-lg">
                Implementation-first reference for Otheryn website, platform concepts, products, integrations, security, and operations. Planned capabilities are explicitly labeled.
              </p>
            </div>
            <div className="spatial-inset p-4 lg:max-w-xs">
              <p className="font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ink/45">Current scope</p>
              <p className="mt-2 text-sm leading-7 text-ink/65">Public website, DentalPilot AI implementation evidence, and planned UETI platform model.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="p-5 sm:p-8 lg:p-12">
        <div className="mx-auto grid w-full max-w-[96rem] gap-6 lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_240px]">
          <div className="hidden lg:block">
            <div className="sticky top-28">{nav}</div>
          </div>

          <div className="min-w-0">
            <div className="mb-4 lg:hidden">
              <button type="button" onClick={() => setMobileNavOpen((v) => !v)} className="btn-secondary w-full justify-between">
                <span>{mobileNavOpen ? 'Close documentation menu' : 'Browse documentation'}</span>
                <span aria-hidden="true">{mobileNavOpen ? '−' : '+'}</span>
              </button>
              {mobileNavOpen && <div className="mt-3">{nav}</div>}
            </div>

            <article className="spatial-surface p-6 sm:p-8 lg:p-10">
              <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-2 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-ink/45">
                <Link to="/documentation" className="hover:text-ink">Documentation</Link>
                <span aria-hidden="true">/</span>
                <span className="text-ink/70">{article.navLabel}</span>
              </nav>

              <div className="mb-8 border-b border-ink/10 pb-8">
                <p className="eyebrow">{article.navLabel}</p>
                <h1 className="mt-4 font-display text-[clamp(2.2rem,4.5vw,4rem)] leading-[0.95] tracking-[-0.04em] text-ink">{article.title}</h1>
                <p className="mt-4 max-w-3xl text-base leading-8 text-ink/65">{article.description}</p>
                <p className="mt-4 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-ink/40">Last updated {article.updated}</p>
              </div>

              <DocBlocks blocks={article.blocks} />

              <div className="mt-12 grid gap-3 border-t border-ink/10 pt-8 sm:grid-cols-2">
                {adjacent.prev ? (
                  <Link to={adjacent.prev.path} className="group rounded-2xl border border-ink/10 bg-white/30 p-4 transition hover:border-ink/20 hover:bg-white/45">
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.12em] text-ink/40">Previous</p>
                    <p className="mt-2 font-display text-2xl tracking-[-0.03em] text-ink group-hover:text-forest">{adjacent.prev.navLabel}</p>
                  </Link>
                ) : <div />}
                {adjacent.next ? (
                  <Link to={adjacent.next.path} className="group rounded-2xl border border-ink/10 bg-white/30 p-4 text-left transition hover:border-ink/20 hover:bg-white/45 sm:text-right">
                    <p className="font-mono text-[0.55rem] uppercase tracking-[0.12em] text-ink/40">Next</p>
                    <p className="mt-2 font-display text-2xl tracking-[-0.03em] text-ink group-hover:text-forest">{adjacent.next.navLabel}</p>
                  </Link>
                ) : <div />}
              </div>
            </article>
          </div>

          <Toc article={article} />
        </div>
      </section>
    </div>
  );
}
