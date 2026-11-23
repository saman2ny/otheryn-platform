// Universal Execution & Trust Infrastructure (UETI) content model.
// Status values are explicit so the site never implies a capability is live when it is not.

export const UETI_NAME = 'Universal Execution & Trust Infrastructure';
export const UETI_TAGLINE = 'Making Every Execution Accountable.';
export const UETI_SUBTAGLINE = 'Every Outcome Verifiable.';

export type CapabilityStatus = 'live' | 'planned' | 'coming-soon';

export type Capability = {
  id: string;
  index: string;
  title: string;
  summary: string;
  detail: string;
  status: CapabilityStatus;
};

// The five platform capabilities. None are implemented in this repository yet,
// so they are all marked planned. Healthcare is the first commercial vertical.
export const capabilities: Capability[] = [
  {
    id: 'identity',
    index: '01',
    title: 'Identity and Authorization',
    summary: 'Know who — or what — is acting, and what they are allowed to do.',
    detail:
      'Verify the identity of people, AI agents and connected systems, and bind every action to an explicit authorization decision before it runs.',
    status: 'planned',
  },
  {
    id: 'policy',
    index: '02',
    title: 'Policy and Governance',
    summary: 'Decide, in one place, how work is allowed to happen.',
    detail:
      'Express organizational policy as enforceable rules, so authorization, escalation and guardrails are applied consistently instead of per-tool.',
    status: 'planned',
  },
  {
    id: 'execution',
    index: '03',
    title: 'Execution and Orchestration',
    summary: 'Route work across people, agents and systems.',
    detail:
      'Coordinate multi-step work across humans, AI agents and connected systems while keeping a single accountable owner for the outcome.',
    status: 'planned',
  },
  {
    id: 'evidence',
    index: '04',
    title: 'Evidence and Verification',
    summary: 'Capture proof as work happens, then check the result.',
    detail:
      'Emit verifiable evidence during execution and confirm the intended outcome actually occurred — not just that an action was attempted.',
    status: 'planned',
  },
  {
    id: 'audit',
    index: '05',
    title: 'Accountability and Audit',
    summary: 'A durable, reviewable record of every action and outcome.',
    detail:
      'Produce audit-ready records that tie authorization, execution and verification together, so any outcome can be explained and reviewed later.',
    status: 'planned',
  },
];

export const problemPoints = [
  {
    title: 'Actions without authorization',
    desc: 'Work is delegated to people and software, but the permission behind each action is rarely recorded in a checkable way.',
  },
  {
    title: 'Outcomes without evidence',
    desc: 'A task can be marked complete without proof that the intended result actually happened.',
  },
  {
    title: 'Records without accountability',
    desc: 'When something goes wrong, the trail linking action, decision and outcome is scattered or missing.',
  },
];

export const flowSteps = [
  { step: '01', title: 'Authorize', desc: 'Identity and policy decide whether an action may run.' },
  { step: '02', title: 'Orchestrate', desc: 'Work is routed to the right person, agent or system.' },
  { step: '03', title: 'Execute', desc: 'The action runs with a clear accountable owner.' },
  { step: '04', title: 'Capture', desc: 'Evidence is recorded as the work happens.' },
  { step: '05', title: 'Verify', desc: 'The outcome is checked and the record is sealed.' },
];

export const principles = [
  { title: 'Authorization first', desc: 'No action runs without an explicit, checkable decision.' },
  { title: 'Evidence by default', desc: 'Proof is captured during execution, not reconstructed afterwards.' },
  { title: 'Audit-ready records', desc: 'Every action and outcome stays reviewable over time.' },
  { title: 'Human and AI oversight', desc: 'People and agents operate under the same accountability.' },
];

export const industries = [
  {
    name: 'Healthcare',
    status: 'live' as CapabilityStatus,
    note: 'DentalPilot AI is the first enabled product built on the platform.',
  },
  {
    name: 'Other industries',
    status: 'planned' as CapabilityStatus,
    note: 'The same accountable layer is designed to apply beyond healthcare over time.',
  },
];

export const statusLabel = (status: CapabilityStatus) => {
  switch (status) {
    case 'live':
      return 'Live';
    case 'coming-soon':
      return 'Coming Soon';
    default:
      return 'Planned';
  }
};