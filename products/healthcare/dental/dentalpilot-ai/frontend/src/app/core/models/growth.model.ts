export interface LocalListingAudit {
  id: string;
  branchId: string;
  platform: string;
  profileUrl: string;
  primaryCategory: string;
  nameMatches: boolean;
  addressMatches: boolean;
  phoneMatches: boolean;
  notes: string;
  lastReviewedAt: string;
}

export interface LocalListingAuditInput {
  branchId: string;
  platform: string;
  profileUrl: string;
  primaryCategory: string;
  nameMatches: boolean;
  addressMatches: boolean;
  phoneMatches: boolean;
  notes: string;
}

export type CampaignStatus = 'draft' | 'planned' | 'active' | 'paused' | 'completed';

export interface MarketingCampaign {
  id: string;
  branchId?: string;
  title: string;
  channel: 'social' | 'email' | 'local' | 'community' | 'other';
  objective: string;
  status: CampaignStatus;
  startAt?: string;
  endAt?: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export interface MarketingCampaignInput {
  branchId?: string;
  title: string;
  channel: MarketingCampaign['channel'];
  objective: string;
  status: 'draft' | 'planned';
  startAt?: string;
  endAt?: string;
  notes: string;
}

export interface ClinicReview {
  id: string;
  branchId?: string;
  platform: string;
  reviewerName: string;
  rating: number;
  reviewText: string;
  responseDraft?: string;
  responseStatus: 'new' | 'drafted';
  reviewDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ClinicReviewInput {
  branchId?: string;
  platform: string;
  reviewerName: string;
  rating: number;
  reviewText: string;
  reviewDate?: string;
}
