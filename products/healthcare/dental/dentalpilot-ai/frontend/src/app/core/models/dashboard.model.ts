export interface DashboardSummary {
  contentGeneratedThisMonth: number;
  postsScheduledUpcoming: number;
  aiCreditsUsed: number;
  aiCreditsLimit: number;
  planTier: string;
  recentContent: {
    id: string;
    headline: string;
    platform: string;
    createdAt: string;
  }[];
  upcomingEvents: {
    id: string;
    title: string;
    platform: string;
    scheduledAt: string;
  }[];
}

export interface RevenueMetrics {
  periodStart: string;
  periodEnd: string;
  currency: string;
  totalRevenue: number;
  treatmentRevenue: number;
  subscriptionRevenue: number;
  patientPaymentsCollected: number;
  insurancePaymentsCollected: number;
  refundsIssued: number;
  netRevenue: number;
  outstandingReceivables: number;
  revenueByCategory: Record<string, number>;
  revenueByPaymentMethod: Record<string, number>;
  monthlyTrend: MonthlyRevenuePoint[];
}

export interface MonthlyRevenuePoint {
  month: string;
  revenue: number;
  treatmentRevenue: number;
  subscriptionRevenue: number;
  patientPayments: number;
  insurancePayments: number;
}

export interface FinancialSummary {
  clinicId: string;
  clinicName: string;
  currency: string;
  periodStart: string;
  periodEnd: string;
  totalCharges: number;
  totalPayments: number;
  totalRefunds: number;
  netCollected: number;
  outstandingBalance: number;
  chargesByType: Record<string, number>;
  paymentsByMethod: Record<string, number>;
  insuranceClaims: InsuranceClaimsSummary;
}

export interface InsuranceClaimsSummary {
  totalClaims: number;
  totalBilled: number;
  totalApproved: number;
  totalPaid: number;
  pendingClaims: number;
  deniedClaims: number;
  approvalRate: number;
  collectionRate: number;
}

export interface TreatmentFollowupMetrics {
  periodStart: string;
  periodEnd: string;
  totalStages: number;
  completedStages: number;
  deferredStages: number;
  declinedStages: number;
  pendingStages: number;
  overdueStages: number;
  completionRate: number;
  conversionRate: number;
  followupSent: number;
  followupCompleted: number;
  followupCompletionRate: number;
  avgDaysToCompletion: number | null;
  followupByType: Record<string, FollowupTypeMetrics>;
}

export interface FollowupTypeMetrics {
  sent: number;
  completed: number;
  completionRate: number;
}

export interface PatientRetentionMetrics {
  periodStart: string;
  periodEnd: string;
  newPatients: number;
  returningPatients: number;
  totalUniquePatients: number;
  retentionRate: number;
  avgVisitsPerPatient: number;
  patientsWithCompletedTreatment: number;
  treatmentCompletionRate: number;
}

export interface ClinicOperationalMetrics {
  periodStart: string;
  periodEnd: string;
  totalVisits: number;
  completedVisits: number;
  cancelledVisits: number;
  noShowVisits: number;
  noShowRate: number;
  scheduledVisits: number;
  totalEnquiries: number;
  convertedEnquiries: number;
  enquiryConversionRate: number;
  avgWaitTimeDays: number | null;
  branchCount: number;
  activeStaffCount: number;
}

export interface OnboardingStep {
  id: string;
  name: string;
  description: string;
  completed: boolean;
  required: boolean;
  order: number;
}

export interface OnboardingStatus {
  currentStep: number;
  totalSteps: number;
  steps: OnboardingStep[];
  profileComplete: boolean;
  branchCount: number;
  staffCount: number;
  subscriptionActive: boolean;
  onboardingCompletedAt: string | null;
  canComplete: boolean;
}
