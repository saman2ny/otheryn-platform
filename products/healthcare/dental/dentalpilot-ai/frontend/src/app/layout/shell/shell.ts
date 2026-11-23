import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

interface NavLink {
  path: string;
  label: string;
  icon: string;
  queryParams?: { tab: string };
}

type WorkflowTab =
  | 'overview'
  | 'journey'
  | 'revenue'
  | 'analytics'
  | 'passport'
  | 'consent'
  | 'governance'
  | 'reminders'
  | 'integrations'
  | 'clinic';

type OperationsTab =
  | 'digital'
  | 'equipment'
  | 'sterilization'
  | 'communication'
  | 'publishing'
  | 'documentation'
  | 'providers';

interface NavGroup {
  label: string;
  links: NavLink[];
}

const WORKFLOW_PATH = '/dentalpilot-workflows';
const OPERATIONS_PATH = '/dental-operations';
const workflowLink = (tab: WorkflowTab, label: string, icon: string): NavLink => ({
  path: WORKFLOW_PATH,
  label,
  icon,
  ...(tab === 'overview' ? {} : { queryParams: { tab } }),
});
const operationsLink = (tab: OperationsTab, label: string, icon: string): NavLink => ({
  path: OPERATIONS_PATH,
  label,
  icon,
  queryParams: { tab },
});

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Practice management',
    links: [
      { path: '/dashboard', label: 'Overview', icon: '◫' },
      { path: '/clinic-profile', label: 'Clinic profile', icon: '⌂' },
      workflowLink('overview', 'Patients & CRM', '◉'),
      workflowLink('clinic', 'Staff & branches', '⌖'),
    ],
  },
  {
    label: 'Dental intelligence',
    links: [
      workflowLink('journey', 'Treatment journey', '◎'),
      workflowLink('revenue', 'Revenue recovery', '◈'),
      workflowLink('analytics', 'Dental analytics', '▤'),
    ],
  },
  {
    label: 'Patient experience',
    links: [
      workflowLink('passport', 'Patient passport', '◉'),
      workflowLink('consent', 'Consent & audit', '⛨'),
      workflowLink('reminders', 'Recall & follow-up', '↻'),
      operationsLink('communication', 'Patient communication', '✉'),
    ],
  },
  {
    label: 'Digital dentistry',
    links: [operationsLink('digital', 'Case coordination', '◈')],
  },
  {
    label: 'Connected dentistry',
    links: [
      operationsLink('equipment', 'Equipment & maintenance', '⚙'),
      operationsLink('sterilization', 'Sterilisation monitoring', '◌'),
      operationsLink('providers', 'Integration catalog', '⛭'),
      workflowLink('integrations', 'PMS data exchange', '⇄'),
    ],
  },
  {
    label: 'Clinic growth',
    links: [
      { path: '/content-generator', label: 'AI content studio', icon: '✦' },
      { path: '/content-calendar', label: 'Content calendar', icon: '▦' },
      {
        path: '/growth-os',
        label: 'Local SEO',
        icon: '⌖',
        queryParams: { tab: 'local-seo' },
      },
      {
        path: '/growth-os',
        label: 'Campaigns',
        icon: '◷',
        queryParams: { tab: 'campaigns' },
      },
      {
        path: '/growth-os',
        label: 'Reviews',
        icon: '☆',
        queryParams: { tab: 'reviews' },
      },
      operationsLink('publishing', 'Publication drafts', '↗'),
      { path: '/export-content', label: 'Export library', icon: '↗' },
    ],
  },
  {
    label: 'Administration',
    links: [
      { path: '/organization-management', label: 'Clinic group', icon: '⌂' },
      workflowLink('governance', 'Security & audit', '⛨'),
      { path: '/billing', label: 'Plan & billing', icon: '◇' },
    ],
  },
];

@Component({
  selector: 'dp-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
})
export class Shell {
  protected readonly auth = inject(AuthService);
  protected readonly navGroups = NAV_GROUPS;
  protected readonly navLinks = NAV_GROUPS.flatMap((group) => group.links);

  protected logout(): void {
    this.auth.logout();
  }
}
