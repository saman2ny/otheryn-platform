import { PlanTier } from './user.model';

export interface SubscriptionPlan {
  tier: PlanTier;
  name: string;
  monthlyPrice: number;
  annualPrice: number;
  aiCreditsPerMonth: number;
  features: string[];
}

export type SubscriptionStatus =
  | 'created'
  | 'authenticated'
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'paused'
  | 'suspended'
  | 'canceled';

export interface Subscription {
  planTier: PlanTier;
  status: SubscriptionStatus;
  billingCycle: 'monthly' | 'annual';
  currentPeriodEnd: string;
  gracePeriodEndsAt?: string;
  cancelAtCycleEnd: boolean;
  paymentFailureCount: number;
  razorpaySubscriptionId?: string;
  aiCreditsUsed: number;
  aiCreditsLimit: number;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  issuedAt: string;
  status: 'paid' | 'open' | 'void';
  downloadUrl?: string;
}

export interface SubscriptionCheckoutRequest {
  planTier: PlanTier;
  billingCycle: 'monthly' | 'annual';
}

export interface SubscriptionCheckoutResponse {
  requiresPayment: boolean;
  /** Present when requiresPayment is true — pass this to Razorpay Checkout as subscription_id. */
  razorpaySubscriptionId?: string;
  keyId?: string;
  shortUrl?: string;
  subscription?: Subscription;
}

export interface VerifySubscriptionRequest {
  razorpayPaymentId: string;
  razorpaySubscriptionId: string;
  razorpaySignature: string;
}

/** Legacy one-time payment verification used for patient treatment payments. */
export interface VerifyPaymentRequest {
  razorpayOrderId: string;
  razorpayPaymentId: string;
  razorpaySignature: string;
}

export interface TreatmentPaymentOrderCreate {
  chargeEntryId: string;
}

export interface TreatmentPaymentOrder {
  orderId: string;
  amount: number;
  currency: string;
  keyId: string;
  chargeEntryId: string;
  balanceAmount: number;
  status: string;
}

export interface TreatmentPaymentVerify {
  paymentId: string;
  ledgerEntryId: string;
  chargeEntryId: string;
  amount: number;
  currency: string;
  status: 'paid';
}

export interface PatientPortalTreatmentCharge {
  chargeEntryId: string;
  amount: number;
  paidAmount: number;
  balanceAmount: number;
  currency: string;
  paymentEnabled: boolean;
}
