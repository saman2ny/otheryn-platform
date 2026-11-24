import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TourService } from '../../core/services/tour.service';

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
    label: 'Workspace',
    links: [
      { path: '/dashboard', label: 'Overview', icon: '◫' },
      { path: '/clinic-profile', label: 'Clinic profile', icon: '⌂' },
      workflowLink('overview', 'Patients & CRM', '◉'),
      workflowLink('clinic', 'Staff & branches', '⌖'),
    ],
  },
  {
    label: 'Dental Intelligence',
    links: [
      workflowLink('journey', 'Treatment journey', '◎'),
      workflowLink('revenue', 'Revenue recovery', '◈'),
      workflowLink('analytics', 'Dental analytics', '▤'),
    ],
  },
  {
    label: 'Patient Experience',
    links: [
      workflowLink('passport', 'Patient passport', '◉'),
      workflowLink('consent', 'Consent & audit', '⛨'),
      workflowLink('reminders', 'Recall & follow-up', '↻'),
      operationsLink('communication', 'Patient communication', '✉'),
      operationsLink('documentation', 'Clinical notes', '✎'),
    ],
  },
  {
    label: 'Digital Dentistry',
    links: [operationsLink('digital', 'Case coordination', '◈')],
  },
  {
    label: 'Connected Dentistry',
    links: [
      operationsLink('equipment', 'Equipment & maintenance', '⚙'),
      operationsLink('sterilization', 'Sterilisation monitoring', '◌'),
      operationsLink('providers', 'Integration catalog', '⛭'),
      workflowLink('integrations', 'PMS data exchange', '⇄'),
    ],
  },
  {
    label: 'Clinic Growth',
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
  private readonly tour = inject(TourService);
  protected readonly navGroups = NAV_GROUPS;
  protected readonly navLinks = NAV_GROUPS.flatMap((group) => group.links);

  constructor() {
    // Start the role-specific guided tour on first login.
    setTimeout(() => this.tour.maybeStart(), 1500);
  }

  protected startTour(): void {
    this.tour.start();
  }

  protected logout(): void {
    this.auth.logout();
  }
}
