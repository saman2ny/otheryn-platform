import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../core/constants/api-endpoints.const';
import {
  ClinicOrganization,
  EditableOrganizationMemberRole,
  OrganizationAnalytics,
  OrganizationInvitation,
  OrganizationMember,
} from '../../core/models/operations.model';

@Injectable({ providedIn: 'root' })
export class OrganizationManagementService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getCurrent(): Observable<ClinicOrganization | null> {
    return this.http.get<ClinicOrganization | null>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.current}`,
    );
  }

  getAnalytics(): Observable<OrganizationAnalytics> {
    return this.http.get<OrganizationAnalytics>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.analytics}`,
    );
  }

  listMembers(): Observable<OrganizationMember[]> {
    return this.http.get<OrganizationMember[]>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.members}`,
    );
  }

  updateMemberRole(
    userId: string,
    role: EditableOrganizationMemberRole,
  ): Observable<OrganizationMember> {
    return this.http.patch<OrganizationMember>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.memberRole(userId)}`,
      { role },
    );
  }

  removeMember(userId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.removeMember(userId)}`,
    );
  }

  create(name: string): Observable<ClinicOrganization> {
    return this.http.post<ClinicOrganization>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.create}`,
      { name },
    );
  }

  inviteClinicOwner(email: string): Observable<OrganizationInvitation> {
    return this.http.post<OrganizationInvitation>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.invitations}`,
      { email },
    );
  }

  acceptInvitation(invitationToken: string): Observable<void> {
    return this.http.post<void>(
      `${this.baseUrl}/${API_ENDPOINTS.organizations.acceptInvitation}`,
      { invitationToken },
    );
  }
}
