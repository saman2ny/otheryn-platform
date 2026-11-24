import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import {
  ClinicOrganization,
  EditableOrganizationMemberRole,
  OrganizationAnalytics,
  OrganizationInvitation,
  OrganizationMember,
} from '../../core/models/operations.model';
import { NotificationService } from '../../core/services/notification.service';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { OrganizationManagementService } from './organization-management.service';

@Component({
  selector: 'dp-organization-management',
  imports: [CurrencyPipe, DatePipe, FormsModule, PageHeader],
  templateUrl: './organization-management.html',
})
export class OrganizationManagement {
  private readonly service = inject(OrganizationManagementService);
  private readonly notifications = inject(NotificationService);

  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly organization = signal<ClinicOrganization | null>(null);
  protected readonly analytics = signal<OrganizationAnalytics | null>(null);
  protected readonly members = signal<OrganizationMember[]>([]);
  protected readonly invitation = signal<OrganizationInvitation | null>(null);
  protected readonly organizationName = signal('');
  protected readonly invitedEmail = signal('');
  protected readonly invitationToken = signal('');
  protected readonly memberRoleEdits = signal<Record<string, EditableOrganizationMemberRole>>({});
  protected readonly canManageRoles = computed(
    () => this.organization()?.currentMemberRole === 'organization-owner',
  );
  protected readonly canManageMembers = computed(() =>
    ['organization-owner', 'organization-admin'].includes(
      this.organization()?.currentMemberRole ?? '',
    ),
  );
  protected readonly canInviteClinics = this.canManageMembers;

  constructor() {
    this.load();
  }

  protected createOrganization(): void {
    const name = this.organizationName().trim();
    if (name.length < 2) {
      this.notifications.error('Enter an organization name with at least two characters.');
      return;
    }
    this.saving.set(true);
    this.service.create(name).subscribe({
      next: (organization) => {
        this.organization.set(organization);
        this.organizationName.set('');
        this.saving.set(false);
        this.notifications.success('Clinic organization created. This clinic is its first member.');
        this.loadGroup();
      },
      error: () => this.saving.set(false),
    });
  }

  protected inviteClinic(): void {
    const email = this.invitedEmail().trim();
    if (!email) {
      this.notifications.error('Enter the clinic owner email address.');
      return;
    }
    this.saving.set(true);
    this.service.inviteClinicOwner(email).subscribe({
      next: (invitation) => {
        this.invitation.set(invitation);
        this.invitedEmail.set('');
        this.saving.set(false);
        this.notifications.success(
          'One-time invitation created. Deliver it securely to the clinic owner.',
        );
      },
      error: () => this.saving.set(false),
    });
  }

  protected acceptInvitation(): void {
    const token = this.invitationToken().trim();
    if (token.length < 32) {
      this.notifications.error('Enter the complete organization invitation token.');
      return;
    }
    this.saving.set(true);
    this.service.acceptInvitation(token).subscribe({
      next: () => {
        this.invitationToken.set('');
        this.saving.set(false);
        this.notifications.success('This clinic joined the organization.');
        this.load();
      },
      error: () => this.saving.set(false),
    });
  }

  protected roleFor(member: OrganizationMember): EditableOrganizationMemberRole {
    return (
      this.memberRoleEdits()[member.userId] ??
      (member.role === 'organization-admin' ? 'organization-admin' : 'reporting-only')
    );
  }

  protected setMemberRole(userId: string, role: EditableOrganizationMemberRole): void {
    this.memberRoleEdits.update((edits) => ({ ...edits, [userId]: role }));
  }

  protected saveMemberRole(member: OrganizationMember): void {
    const role = this.roleFor(member);
    this.saving.set(true);
    this.service.updateMemberRole(member.userId, role).subscribe({
      next: (updatedMember) => {
        this.members.update((members) =>
          members.map((item) => (item.userId === updatedMember.userId ? updatedMember : item)),
        );
        this.memberRoleEdits.update((edits) => {
          const next = { ...edits };
          delete next[member.userId];
          return next;
        });
        this.saving.set(false);
        this.notifications.success('Organization member role updated.');
      },
      error: () => this.saving.set(false),
    });
  }

  protected removeMember(member: OrganizationMember): void {
    if (!globalThis.confirm(`Remove ${member.fullName}'s clinic from this organization?`)) return;
    this.saving.set(true);
    this.service.removeMember(member.userId).subscribe({
      next: () => {
        this.members.update((members) => members.filter((item) => item.userId !== member.userId));
        this.saving.set(false);
        this.notifications.success(
          'Clinic removed from the organization. Its clinic data was retained.',
        );
        this.loadGroup();
      },
      error: () => this.saving.set(false),
    });
  }

  protected roleLabel(role: OrganizationMember['role']): string {
    switch (role) {
      case 'organization-owner':
        return 'Organization owner';
      case 'organization-admin':
        return 'Organization admin';
      case 'reporting-only':
        return 'Reporting only';
      case 'clinic-owner':
        return 'Clinic owner';
    }
  }

  private load(): void {
    this.loading.set(true);
    this.service.getCurrent().subscribe({
      next: (organization) => {
        this.organization.set(organization);
        if (organization) this.loadGroup();
        else this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.notifications.error('Unable to load organization information.');
      },
    });
  }

  private loadGroup(): void {
    const memberList = this.canManageMembers() ? this.service.listMembers() : of([]);
    forkJoin({
      analytics: this.service.getAnalytics(),
      members: memberList,
    }).subscribe({
      next: (result) => {
        this.analytics.set(result.analytics);
        this.members.set(result.members);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.notifications.error('Unable to load organization reporting.');
      },
    });
  }
}
