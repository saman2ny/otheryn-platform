import { DatePipe } from '@angular/common';
import { Component, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, of, switchMap } from 'rxjs';
import {
  DashboardSummary,
  RevenueMetrics,
  FinancialSummary,
  TreatmentFollowupMetrics,
  PatientRetentionMetrics,
  ClinicOperationalMetrics,
  OnboardingStatus,
} from '../../core/models/dashboard.model';
import { EmptyState } from '../../shared/ui/empty-state/empty-state';
import { StatCard } from '../../shared/ui/stat-card/stat-card';
import { DashboardService } from './dashboard.service';

type DashboardTab = 'overview' | 'revenue' | 'treatment' | 'patients' | 'operations';

@Component({
  selector: 'dp-dashboard',
  imports: [EmptyState, DatePipe, StatCard],
  templateUrl: './dashboard.html',
})
export class Dashboard {
  private readonly dashboardService = inject(DashboardService);
  private readonly router = inject(Router);

  protected readonly summary = signal<DashboardSummary | null>(null);
  protected readonly revenueMetrics = signal<RevenueMetrics | null>(null);
  protected readonly financialSummary = signal<FinancialSummary | null>(null);
  protected readonly treatmentFollowup = signal<TreatmentFollowupMetrics | null>(null);
  protected readonly patientRetention = signal<PatientRetentionMetrics | null>(null);
  protected readonly operationalMetrics = signal<ClinicOperationalMetrics | null>(null);
  protected readonly onboardingStatus = signal<OnboardingStatus | null>(null);
  protected readonly loadFailed = signal(false);
  protected readonly activeTab = signal<DashboardTab>('overview');
  protected readonly dateRange = signal<{ from?: string; to?: string }>({});

  protected readonly Object = Object;

  constructor() {
    this.loadOverview();
    this.loadOnboarding();
  }

  private loadOverview(): void {
    this.dashboardService
      .getSummary()
      .pipe(
        catchError(() => {
          this.loadFailed.set(true);
          return of(null);
        }),
      )
      .subscribe((summary) => this.summary.set(summary));
  }

  private loadOnboarding(): void {
    this.dashboardService
      .getOnboardingStatus()
      .pipe(catchError(() => of(null)))
      .subscribe((status) => this.onboardingStatus.set(status));
  }

  protected loadTabData(): void {
    const { from, to } = this.dateRange();
    switch (this.activeTab()) {
      case 'revenue':
        this.dashboardService.getRevenueMetrics(from, to).subscribe((data) => this.revenueMetrics.set(data));
        this.dashboardService.getFinancialSummary(from, to).subscribe((data) => this.financialSummary.set(data));
        break;
      case 'treatment':
        this.dashboardService.getTreatmentFollowupMetrics(from, to).subscribe((data) => this.treatmentFollowup.set(data));
        break;
      case 'patients':
        this.dashboardService.getPatientRetentionMetrics(from, to).subscribe((data) => this.patientRetention.set(data));
        break;
      case 'operations':
        this.dashboardService.getOperationalMetrics(from, to).subscribe((data) => this.operationalMetrics.set(data));
        break;
    }
  }

  protected setTab(tab: DashboardTab): void {
    this.activeTab.set(tab);
    this.loadTabData();
  }

  protected updateDateRange(from?: string, to?: string): void {
    this.dateRange.set({ from, to });
    this.loadTabData();
  }

  protected get today(): string {
    return new Date().toISOString().split('T')[0];
  }

  protected get thirtyDaysAgo(): string {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  }

  protected goToContentGenerator(): void {
    this.router.navigateByUrl('/content-generator');
  }

  protected goToCalendar(): void {
    this.router.navigateByUrl('/content-calendar');
  }

  protected goToPatientJourneys(): void {
    this.router.navigateByUrl('/dentalpilot-workflows');
  }

  protected goToBilling(): void {
    this.router.navigateByUrl('/billing');
  }

  protected formatCurrency(amount: number, currency = 'INR'): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }

  protected formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
  }

  protected readonly overviewStats = computed(() => {
    const s = this.summary();
    if (!s) return [];
    return [
      { label: 'Content This Month', value: s.contentGeneratedThisMonth, icon: '📝' },
      { label: 'Scheduled Posts', value: s.postsScheduledUpcoming, icon: '📅' },
      { label: 'AI Credits Used', value: `${s.aiCreditsUsed}/${s.aiCreditsLimit}`, icon: '🤖' },
      { label: 'Plan', value: s.planTier, icon: '💎' },
    ];
  });

  protected readonly revenueStats = computed(() => {
    const r = this.revenueMetrics();
    if (!r) return [];
    return [
      { label: 'Total Revenue', value: this.formatCurrency(r.totalRevenue, r.currency), icon: '💰' },
      { label: 'Treatment Revenue', value: this.formatCurrency(r.treatmentRevenue, r.currency), icon: '🦷' },
      { label: 'Subscription Revenue', value: this.formatCurrency(r.subscriptionRevenue, r.currency), icon: '📋' },
      { label: 'Net Revenue', value: this.formatCurrency(r.netRevenue, r.currency), icon: '📈' },
    ];
  });

  protected readonly financialStats = computed(() => {
    const f = this.financialSummary();
    if (!f) return [];
    return [
      { label: 'Total Charges', value: this.formatCurrency(f.totalCharges, f.currency), icon: '📊' },
      { label: 'Total Payments', value: this.formatCurrency(f.totalPayments, f.currency), icon: '💵' },
      { label: 'Outstanding', value: this.formatCurrency(f.outstandingBalance, f.currency), icon: '⏳' },
      { label: 'Insurance Collection', value: this.formatPercent(f.insuranceClaims.collectionRate), icon: '🏥' },
    ];
  });

  protected readonly treatmentStats = computed(() => {
    const t = this.treatmentFollowup();
    if (!t) return [];
    return [
      { label: 'Total Stages', value: t.totalStages, icon: '📋' },
      { label: 'Completed', value: t.completedStages, icon: '✅' },
      { label: 'Completion Rate', value: this.formatPercent(t.completionRate), icon: '📈' },
      { label: 'Overdue', value: t.overdueStages, icon: '⚠️' },
    ];
  });

  protected readonly patientStats = computed(() => {
    const p = this.patientRetention();
    if (!p) return [];
    return [
      { label: 'New Patients', value: p.newPatients, icon: '👤' },
      { label: 'Returning', value: p.returningPatients, icon: '🔄' },
      { label: 'Retention Rate', value: this.formatPercent(p.retentionRate), icon: '📊' },
      { label: 'Treatment Completion', value: this.formatPercent(p.treatmentCompletionRate), icon: '✅' },
    ];
  });

  protected readonly operationalStats = computed(() => {
    const o = this.operationalMetrics();
    if (!o) return [];
    return [
      { label: 'Total Visits', value: o.totalVisits, icon: '🏥' },
      { label: 'Completed', value: o.completedVisits, icon: '✅' },
      { label: 'No-Show Rate', value: this.formatPercent(o.noShowRate), icon: '📉' },
      { label: 'Enquiry Conversion', value: this.formatPercent(o.enquiryConversionRate), icon: '📈' },
    ];
  });

  protected readonly revenueCategories = computed(() => {
    const r = this.revenueMetrics();
    if (!r) return [];
    return Object.entries(r.revenueByCategory).map(([key, value]) => ({
      key: key.replace('_', ' '),
      value: this.formatCurrency(value, r.currency),
    }));
  });

  protected readonly paymentMethods = computed(() => {
    const f = this.financialSummary();
    if (!f) return [];
    return Object.entries(f.paymentsByMethod).map(([key, value]) => ({
      key: key,
      value: this.formatCurrency(value, f.currency),
    }));
  });

  protected readonly followupTypes = computed(() => {
    const t = this.treatmentFollowup();
    if (!t) return [];
    return Object.entries(t.followupByType).map(([type, m]) => ({
      type: type.replace('-', ' '),
      completionRate: this.formatPercent(m.completionRate),
      sent: m.sent,
      completed: m.completed,
    }));
  });

  protected readonly onboardingProgress = computed(() => {
    const o = this.onboardingStatus();
    if (!o) return null;
    const completed = o.steps.filter(s => s.completed).length;
    const requiredCompleted = o.steps.filter(s => s.required && s.completed).length;
    const requiredTotal = o.steps.filter(s => s.required).length;
    return {
      percent: Math.round((completed / o.totalSteps) * 100),
      completed,
      total: o.totalSteps,
      requiredPercent: requiredTotal > 0 ? Math.round((requiredCompleted / requiredTotal) * 100) : 100,
      canComplete: o.canComplete,
    };
  });
}