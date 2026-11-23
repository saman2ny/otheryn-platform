import { DatePipe, DecimalPipe, TitleCasePipe, UpperCasePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import {
  Invoice,
  Subscription,
  SubscriptionCheckoutResponse,
  SubscriptionPlan,
} from '../../core/models/billing.model';
import { AuthService } from '../../core/services/auth.service';
import { NotificationService } from '../../core/services/notification.service';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { BillingService } from './billing.service';
import { StatCard } from '../../shared/ui/stat-card/stat-card';

@Component({
  selector: 'dp-billing',
  imports: [PageHeader, DatePipe, DecimalPipe, TitleCasePipe, UpperCasePipe, StatCard],
  templateUrl: './billing.html',
})
export class Billing {
  private readonly billingService = inject(BillingService);
  private readonly notifications = inject(NotificationService);
  private readonly auth = inject(AuthService);

  protected readonly canManage = this.auth.canManageClinic;
  protected readonly plans = signal<SubscriptionPlan[]>([]);
  protected readonly subscription = signal<Subscription | null>(null);
  protected readonly invoices = signal<Invoice[]>([]);
  protected readonly billingCycle = signal<'monthly' | 'annual'>('monthly');
  protected readonly checkingOutTier = signal<string | null>(null);
  protected readonly managingSubscription = signal(false);
  protected readonly activeTab = signal<'plans' | 'usage' | 'invoices' | 'payment-methods'>('plans');

  protected readonly creditsUsagePercent = computed(() => {
    const sub = this.subscription();
    if (!sub || sub.aiCreditsLimit === 0) {
      return 0;
    }
    return Math.min(100, Math.round((sub.aiCreditsUsed / sub.aiCreditsLimit) * 100));
  });

  protected readonly daysUntilRenewal = computed(() => {
    const sub = this.subscription();
    if (!sub?.currentPeriodEnd) return 0;
    return Math.max(0, Math.ceil((new Date(sub.currentPeriodEnd).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
  });

  protected readonly daysUntilReset = computed(() => {
    const sub = this.subscription();
    if (!sub?.currentPeriodEnd) return 0;
    return Math.max(0, Math.ceil((new Date(sub.currentPeriodEnd).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
  });

  protected readonly subscriptionStats = computed(() => {
    const sub = this.subscription();
    if (!sub) return [];
    return [
      { label: 'Plan', value: sub.planTier.charAt(0).toUpperCase() + sub.planTier.slice(1), icon: '💎' },
      { label: 'Status', value: sub.status, icon: sub.status === 'active' ? '✅' : sub.status === 'trialing' ? '⏳' : sub.status === 'past_due' ? '⚠️' : '❌' },
      { label: 'Billing Cycle', value: sub.billingCycle, icon: '🔄' },
      { label: 'Renews In', value: `${this.daysUntilRenewal()} days`, icon: '📅' },
    ];
  });

  protected readonly usageStats = computed(() => {
    const sub = this.subscription();
    if (!sub) return [];
    const remaining = Math.max(0, sub.aiCreditsLimit - sub.aiCreditsUsed);
    return [
      { label: 'AI Credits Used', value: `${sub.aiCreditsUsed}/${sub.aiCreditsLimit}`, icon: '🤖' },
      { label: 'Credits Remaining', value: remaining.toString(), icon: '💚' },
      { label: 'Usage Rate', value: `${this.creditsUsagePercent()}%`, icon: '📊' },
      { label: 'Days Until Reset', value: `${this.daysUntilReset()} days`, icon: '⏱️' },
    ];
  });

  protected readonly planComparison = computed(() => {
    return this.plans().map(plan => ({
      ...plan,
      annualSavingsPercent: Math.round((1 - plan.annualPrice / (plan.monthlyPrice * 12)) * 100),
    }));
  });

  constructor() {
    this.billingService
      .getPlans()
      .pipe(catchError(() => of([])))
      .subscribe((plans) => this.plans.set(plans));

    this.loadSubscription();
    this.loadInvoices();
  }

  protected setTab(tab: 'plans' | 'usage' | 'invoices' | 'payment-methods'): void {
    this.activeTab.set(tab);
  }

  protected selectPlan(plan: SubscriptionPlan): void {
    this.checkingOutTier.set(plan.tier);
    this.billingService
      .createSubscription({ planTier: plan.tier, billingCycle: this.billingCycle() })
      .subscribe({
        next: (order) => {
          if (!order.requiresPayment) {
            this.checkingOutTier.set(null);
            if (order.subscription) {
              this.subscription.set(order.subscription);
            }
            this.notifications.success(`Switched to the ${plan.name} plan.`);
            return;
          }
          this.openRazorpayCheckout(plan, order);
        },
        error: () => {
          this.checkingOutTier.set(null);
          this.notifications.error('Unable to start checkout right now.');
        },
      });
  }

  protected manageSubscription(action: 'cancel' | 'pause' | 'resume'): void {
    this.managingSubscription.set(true);
    const request =
      action === 'cancel'
        ? this.billingService.cancelSubscription()
        : action === 'pause'
          ? this.billingService.pauseSubscription()
          : this.billingService.resumeSubscription();
    request.subscribe({
      next: (subscription) => {
        this.subscription.set(subscription);
        this.managingSubscription.set(false);
        this.notifications.success(
          action === 'cancel'
            ? 'Cancellation is scheduled for the end of the current billing period.'
            : action === 'pause'
              ? 'Pause requested. Razorpay will confirm the change shortly.'
              : 'Resume requested. Razorpay will confirm the change shortly.',
        );
      },
      error: () => {
        this.managingSubscription.set(false);
        this.notifications.error('Unable to update the subscription right now.');
      },
    });
  }

  private openRazorpayCheckout(plan: SubscriptionPlan, order: SubscriptionCheckoutResponse): void {
    const user = this.auth.currentUser();
    if (!order.keyId || !order.razorpaySubscriptionId) {
      this.checkingOutTier.set(null);
      this.notifications.error('Checkout could not be initialized. Please try again.');
      return;
    }
    const subscriptionId = order.razorpaySubscriptionId;

    const razorpay = new Razorpay({
      key: order.keyId,
      subscription_id: subscriptionId,
      name: 'DentalPilot AI',
      description: `${plan.name} plan — ${this.billingCycle()}`,
      prefill: { name: user?.fullName, email: user?.email },
      theme: { color: '#0f766e' },
      handler: (response) => {
        this.billingService
          .verifySubscription({
            razorpayPaymentId: response.razorpay_payment_id,
            razorpaySubscriptionId: subscriptionId,
            razorpaySignature: response.razorpay_signature,
          })
          .subscribe({
            next: (subscription) => {
              this.checkingOutTier.set(null);
              this.subscription.set(subscription);
              this.loadInvoices();
              this.notifications.success(
                'Authorization confirmed. Your plan will activate when Razorpay confirms it.',
              );
            },
            error: () => {
              this.checkingOutTier.set(null);
              this.notifications.error(
                'Payment verification failed. If you were charged, contact support before retrying.',
              );
            },
          });
      },
      modal: {
        ondismiss: () => this.checkingOutTier.set(null),
      },
    });

    razorpay.on('payment.failed', (response) => {
      this.checkingOutTier.set(null);
      this.notifications.error(response.error.description || 'Payment failed. Please try again.');
    });

    razorpay.open();
  }

  private loadSubscription(): void {
    this.billingService
      .getSubscription()
      .pipe(catchError(() => of(null)))
      .subscribe((subscription) => this.subscription.set(subscription));
  }

  private loadInvoices(): void {
    this.billingService
      .getInvoices()
      .pipe(catchError(() => of([])))
      .subscribe((invoices) => this.invoices.set(invoices));
  }
}
