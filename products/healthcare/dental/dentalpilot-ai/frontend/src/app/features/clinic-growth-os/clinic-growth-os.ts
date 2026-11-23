import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ClinicBranch } from '../../core/models/healthcare.model';
import {
  CampaignStatus,
  ClinicReview,
  LocalListingAudit,
  MarketingCampaign,
} from '../../core/models/growth.model';
import { NotificationService } from '../../core/services/notification.service';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { ClinicGrowthOsService } from './clinic-growth-os.service';

const GROWTH_TABS = ['local-seo', 'campaigns', 'reviews'] as const;
type GrowthTab = (typeof GROWTH_TABS)[number];

const isGrowthTab = (value: string | null): value is GrowthTab =>
  GROWTH_TABS.some((tab) => tab === value);

const GROWTH_TITLES: Record<GrowthTab, string> = {
  'local-seo': 'Local SEO & listings',
  campaigns: 'Marketing campaigns',
  reviews: 'Review management',
};

const CAMPAIGN_TRANSITIONS: Record<CampaignStatus, CampaignStatus[]> = {
  draft: ['planned'],
  planned: ['active', 'paused'],
  active: ['paused', 'completed'],
  paused: ['planned', 'active'],
  completed: [],
};

@Component({
  selector: 'dp-clinic-growth-os',
  imports: [DatePipe, FormsModule, PageHeader],
  templateUrl: './clinic-growth-os.html',
})
export class ClinicGrowthOs {
  private readonly service = inject(ClinicGrowthOsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationService);

  protected readonly activeTab = signal<GrowthTab>('local-seo');
  protected readonly pageTitle = computed(() => GROWTH_TITLES[this.activeTab()]);
  protected readonly tabs: { key: GrowthTab; label: string }[] = [
    { key: 'local-seo', label: 'Local SEO' },
    { key: 'campaigns', label: 'Campaigns' },
    { key: 'reviews', label: 'Reviews' },
  ];
  protected readonly branches = signal<ClinicBranch[]>([]);
  protected readonly listings = signal<LocalListingAudit[]>([]);
  protected readonly campaigns = signal<MarketingCampaign[]>([]);
  protected readonly reviews = signal<ClinicReview[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);

  protected readonly listingForm = {
    branchId: '',
    platform: 'Google Business Profile',
    profileUrl: '',
    primaryCategory: '',
    nameMatches: false,
    addressMatches: false,
    phoneMatches: false,
    notes: '',
  };
  protected readonly campaignForm = {
    branchId: '',
    title: '',
    channel: 'social' as MarketingCampaign['channel'],
    objective: '',
    status: 'draft' as 'draft' | 'planned',
    startAt: '',
    endAt: '',
    notes: '',
  };
  protected readonly reviewForm = {
    branchId: '',
    platform: 'Google',
    reviewerName: '',
    rating: 5,
    reviewText: '',
    reviewDate: '',
  };

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab');
      this.activeTab.set(isGrowthTab(tab) ? tab : 'local-seo');
    });
    this.load();
  }

  protected setTab(tab: GrowthTab): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      queryParamsHandling: 'merge',
    });
  }

  protected saveListing(): void {
    if (!this.listingForm.branchId || !this.listingForm.platform.trim()) {
      this.notifications.error('Select a clinic branch and listing platform.');
      return;
    }
    this.saving.set(true);
    this.service
      .saveLocalListing({
        ...this.listingForm,
        platform: this.listingForm.platform.trim(),
        profileUrl: this.listingForm.profileUrl.trim(),
        primaryCategory: this.listingForm.primaryCategory.trim(),
        notes: this.listingForm.notes.trim(),
      })
      .subscribe({
        next: (listing) => {
          this.listings.update((items) => [
            listing,
            ...items.filter((item) => item.id !== listing.id),
          ]);
          this.saving.set(false);
          this.notifications.success('Local listing audit saved.');
        },
        error: () => this.saving.set(false),
      });
  }

  protected createCampaign(): void {
    if (this.campaignForm.title.trim().length < 2) {
      this.notifications.error('Enter a campaign title.');
      return;
    }
    this.saving.set(true);
    this.service
      .createCampaign({
        ...(this.campaignForm.branchId ? { branchId: this.campaignForm.branchId } : {}),
        title: this.campaignForm.title.trim(),
        channel: this.campaignForm.channel,
        objective: this.campaignForm.objective.trim(),
        status: this.campaignForm.status,
        ...(this.campaignForm.startAt
          ? { startAt: new Date(this.campaignForm.startAt).toISOString() }
          : {}),
        ...(this.campaignForm.endAt
          ? { endAt: new Date(this.campaignForm.endAt).toISOString() }
          : {}),
        notes: this.campaignForm.notes.trim(),
      })
      .subscribe({
        next: (campaign) => {
          this.campaigns.update((items) => [campaign, ...items]);
          this.campaignForm.title = '';
          this.campaignForm.objective = '';
          this.campaignForm.startAt = '';
          this.campaignForm.endAt = '';
          this.campaignForm.notes = '';
          this.saving.set(false);
          this.notifications.success('Campaign added to the planning board.');
        },
        error: () => this.saving.set(false),
      });
  }

  protected campaignStatuses(status: CampaignStatus): CampaignStatus[] {
    return [status, ...CAMPAIGN_TRANSITIONS[status]];
  }

  protected branchName(branchId: string): string {
    return this.branches().find((branch) => branch.id === branchId)?.name ?? 'Unknown branch';
  }

  protected listingIsConsistent(listing: LocalListingAudit): boolean {
    return listing.nameMatches && listing.addressMatches && listing.phoneMatches;
  }

  protected updateCampaignStatus(campaignId: string, status: CampaignStatus): void {
    this.service.updateCampaignStatus(campaignId, status).subscribe({
      next: (updated) => {
        this.campaigns.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.notifications.success('Campaign status updated.');
      },
    });
  }

  protected createReview(): void {
    if (!this.reviewForm.platform.trim() || !this.reviewForm.reviewText.trim()) {
      this.notifications.error('Enter the review platform and review text.');
      return;
    }
    this.saving.set(true);
    this.service
      .createReview({
        ...(this.reviewForm.branchId ? { branchId: this.reviewForm.branchId } : {}),
        platform: this.reviewForm.platform.trim(),
        reviewerName: this.reviewForm.reviewerName.trim(),
        rating: Number(this.reviewForm.rating),
        reviewText: this.reviewForm.reviewText.trim(),
        ...(this.reviewForm.reviewDate
          ? { reviewDate: new Date(this.reviewForm.reviewDate).toISOString() }
          : {}),
      })
      .subscribe({
        next: (review) => {
          this.reviews.update((items) => [review, ...items]);
          this.reviewForm.reviewerName = '';
          this.reviewForm.reviewText = '';
          this.reviewForm.reviewDate = '';
          this.saving.set(false);
          this.notifications.success('Review added to the clinic inbox.');
        },
        error: () => this.saving.set(false),
      });
  }

  protected saveReviewDraft(reviewId: string, draft: string): void {
    this.service.saveReviewDraft(reviewId, draft).subscribe({
      next: (updated) => {
        this.reviews.update((items) =>
          items.map((item) => (item.id === updated.id ? updated : item)),
        );
        this.notifications.success(
          updated.responseDraft
            ? 'Response draft saved. It has not been published.'
            : 'Response draft cleared.',
        );
      },
    });
  }

  private load(): void {
    forkJoin({
      branches: this.service.listBranches(),
      listings: this.service.listLocalListings(),
      campaigns: this.service.listCampaigns(),
      reviews: this.service.listReviews(),
    }).subscribe({
      next: (result) => {
        this.branches.set(result.branches);
        this.listings.set(result.listings);
        this.campaigns.set(result.campaigns);
        this.reviews.set(result.reviews);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.notifications.error('Unable to load clinic growth data. Please retry.');
      },
    });
  }
}
