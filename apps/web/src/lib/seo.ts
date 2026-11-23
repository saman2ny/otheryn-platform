import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export type RouteMeta = {
  title: string;
  description: string;
};

const SITE_NAME = 'Otheryn';

// Per-route document metadata. Titles stay concise and avoid keyword stuffing.
export const routeMeta: Record<string, RouteMeta> = {
  '/': {
    title: 'Otheryn — Universal Execution & Trust Infrastructure',
    description:
      'Otheryn is Universal Execution & Trust Infrastructure for governed actions, verifiable execution and accountable outcomes across organizations.',
  },
  '/about': {
    title: 'About — Otheryn',
    description:
      'Why Otheryn exists: closing the gap between executing an action and verifying its outcome with authorization, evidence and accountability.',
  },
  '/platform': {
    title: 'Platform — Otheryn',
    description:
      'The Otheryn platform capabilities: identity and authorization, policy and governance, execution and orchestration, evidence and verification, and accountability and audit.',
  },
  '/architecture': {
    title: 'Architecture — Otheryn',
    description:
      'How the Otheryn Universal Platform is structured across its core capabilities and industry solutions, with planned and live status clearly marked.',
  },
  '/products': {
    title: 'Products — Otheryn',
    description:
      'Specialty products built on one accountable foundation. DentalPilot AI is the first enabled healthcare product.',
  },
  '/solutions': {
    title: 'Solutions — Otheryn',
    description:
      'How Otheryn connects the work between appointments, steps and handoffs with an accountable execution layer.',
  },
  '/industries': {
    title: 'Industries — Otheryn',
    description:
      'Healthcare is the first vertical for Otheryn, with additional industries planned on the same accountable foundation.',
  },
  '/partners': {
    title: 'Partners — Otheryn',
    description: 'Build the Otheryn platform with technology and channel partners.',
  },
  '/security': {
    title: 'Security — Otheryn',
    description: 'How Otheryn approaches trust, security and data protection.',
  },
  '/pricing': {
    title: 'Pricing — Otheryn',
    description: 'Straightforward Otheryn plans for solo clinicians, growing groups and multi-location organizations.',
  },
  '/contact': {
    title: 'Contact — Otheryn',
    description: 'Start a conversation with the Otheryn team.',
  },
  '/book': {
    title: 'Book a Walkthrough — Otheryn',
    description: 'Book a 30-minute Otheryn walkthrough built around your workflow.',
  },
  '/checkout': {
    title: 'Checkout — Otheryn',
    description: 'Activate your Otheryn plan.',
  },
  '/careers': {
    title: 'Careers — Otheryn',
    description: 'Build Universal Execution & Trust Infrastructure with Otheryn.',
  },
  '/blog': {
    title: 'Blog — Otheryn',
    description: 'Field notes on building accountable execution infrastructure.',
  },
  '/faq': {
    title: 'FAQ — Otheryn',
    description: 'Answers about the Otheryn platform, security and implementation.',
  },
  '/privacy': {
    title: 'Privacy — Otheryn',
    description: 'How Otheryn handles your data.',
  },
  '/cookie-policy': {
    title: 'Cookie Policy — Otheryn',
    description: 'How Otheryn uses cookies and similar technologies.',
  },
  '/terms': {
    title: 'Terms — Otheryn',
    description: 'The terms of using Otheryn services.',
  },
};

const DEFAULT_META: RouteMeta = {
  title: `${SITE_NAME} — Universal Execution & Trust Infrastructure`,
  description:
    'Otheryn is Universal Execution & Trust Infrastructure for governed actions, verifiable execution and accountable outcomes across organizations.',
};

const upsertMeta = (
  selector: string,
  attribute: 'name' | 'property',
  key: string,
  content: string,
) => {
  let element = document.head.querySelector<HTMLMetaElement>(selector);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attribute, key);
    document.head.appendChild(element);
  }
  element.setAttribute('content', content);
};

const applyMeta = (meta: RouteMeta) => {
  document.title = meta.title;
  upsertMeta('meta[name="description"]', 'name', 'description', meta.description);
  upsertMeta('meta[property="og:site_name"]', 'property', 'og:site_name', SITE_NAME);
  upsertMeta('meta[property="og:type"]', 'property', 'og:type', 'website');
  upsertMeta('meta[property="og:title"]', 'property', 'og:title', meta.title);
  upsertMeta('meta[property="og:description"]', 'property', 'og:description', meta.description);
  upsertMeta('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary');
  upsertMeta('meta[name="twitter:title"]', 'name', 'twitter:title', meta.title);
  upsertMeta('meta[name="twitter:description"]', 'name', 'twitter:description', meta.description);
};

// Applies per-route metadata on navigation. Rendered once inside the router.
export default function RouteMeta() {
  const { pathname } = useLocation();

  useEffect(() => {
    applyMeta(routeMeta[pathname] ?? DEFAULT_META);
  }, [pathname]);

  return null;
}