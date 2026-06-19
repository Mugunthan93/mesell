/**
 * RazorpayCheckoutService — Razorpay Checkout.js SDK loader + widget lifecycle.
 *
 * Lazily injects the Razorpay Checkout.js script on first use (not in index.html
 * — keeps the external origin isolated to the billing remote). Caches the load
 * promise so the script is only appended once per page lifetime.
 *
 * SCOPE: this service only loads the SDK and opens the widget. It resolves a
 * CheckoutResult that the Plans component uses to transition the state machine.
 * The actual plan grant happens via polling (NOT from the Razorpay callback).
 *
 * Key contract rules (WAVE5_FRONTEND_TASKSPEC.md §5):
 *  - key_id is the PUBLIC Razorpay key from the subscribe response — safe in browser.
 *  - Recurring tiers: pass razorpay_subscription_id.
 *  - LTD: pass razorpay_order_id + amount_paise.
 *  - short_url fallback: open in new tab when in-page widget cannot load.
 *  - BOTH handler (payment submitted) and modal.ondismiss (user closed)
 *    → transition to POLLING state. Neither is the source of truth.
 *  - The cancel (ondismiss without payment) vs pending (payment submitted)
 *    distinction is surfaced via CheckoutResult.status.
 *
 * CSP note (D-FE4): Razorpay checkout.js + api.razorpay.com + lumberjack CDN
 * origins must be allowlisted in the production CSP. FE owns the list entries;
 * infra owns the mechanism. Dev has no CSP — build is unblocked.
 */

import { Injectable } from '@angular/core';
import type { BillingCheckout } from '../billing.model';

const CHECKOUT_JS_URL = 'https://checkout.razorpay.com/v1/checkout.js';

/** Minimum Razorpay global type needed to open the widget. */
interface RazorpayInstance {
  open(): void;
}

interface RazorpayConstructor {
  new(options: Record<string, unknown>): RazorpayInstance;
}

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

/** Result returned when the Razorpay widget closes. */
export interface CheckoutResult {
  /**
   * 'payment_submitted': handler callback fired — user completed the payment flow.
   *   → transition to PENDING and start polling.
   * 'cancelled': modal.ondismiss fired with no payment — user backed out.
   *   → transition to CANCELLED (NOT an error).
   * 'short_url_opened': in-page widget could not load; short_url opened in new tab.
   *   → transition to PENDING and start polling (user may have completed payment externally).
   */
  status: 'payment_submitted' | 'cancelled' | 'short_url_opened';
}

@Injectable()
export class RazorpayCheckoutService {
  /** Cached SDK load promise — script is appended only once. */
  private _sdkLoadPromise: Promise<void> | null = null;

  /**
   * Load Razorpay Checkout.js lazily.
   * Safe to call multiple times — returns the cached promise after first call.
   * Rejects if the script fails to load (network error / CSP block).
   */
  loadSdk(): Promise<void> {
    if (this._sdkLoadPromise) {
      return this._sdkLoadPromise;
    }

    // If window.Razorpay is already defined (e.g. SSR / test mock), resolve immediately.
    if (typeof window !== 'undefined' && window.Razorpay) {
      this._sdkLoadPromise = Promise.resolve();
      return this._sdkLoadPromise;
    }

    this._sdkLoadPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = CHECKOUT_JS_URL;
      script.async = true;
      script.onload  = () => resolve();
      script.onerror = () => {
        // Reset so a subsequent call can retry the load.
        this._sdkLoadPromise = null;
        reject(new Error('Razorpay Checkout.js failed to load'));
      };
      document.head.appendChild(script);
    });

    return this._sdkLoadPromise;
  }

  /**
   * Open the Razorpay checkout widget for the given BillingCheckout handle.
   *
   * Algorithm:
   *   1. Load SDK (cached after first call).
   *   2. Determine widget type (subscription vs order).
   *   3. Open in-page widget with handler + ondismiss callbacks.
   *   4. If window.Razorpay is not available after load (CSP blocked), fall back
   *      to short_url (open in new tab) and resolve with 'short_url_opened'.
   *
   * Returns a Promise<CheckoutResult> that resolves when the widget closes —
   * either from a payment submission, a cancellation, or a short_url fallback.
   * The promise NEVER rejects (errors surface as error states in the component).
   *
   * Called by Plans component AFTER POST /billing/subscribe returns 201.
   */
  openWidget(checkout: BillingCheckout): Promise<CheckoutResult> {
    return this.loadSdk()
      .then(() => this._openInPageWidget(checkout))
      .catch((sdkError: unknown) => {
        console.error('[RazorpayCheckoutService] SDK load failed:', sdkError);
        return this._fallbackToShortUrl(checkout);
      });
  }

  // ─── Private helpers ────────────────────────────────────────────────────────

  private _openInPageWidget(checkout: BillingCheckout): Promise<CheckoutResult> {
    const RazorpayConstructor = window.Razorpay;
    if (!RazorpayConstructor) {
      // SDK loaded but constructor not present (CSP stripped the script body)
      return this._fallbackToShortUrl(checkout);
    }

    return new Promise<CheckoutResult>((resolve) => {
      let paymentSubmitted = false;

      const options: Record<string, unknown> = {
        key: checkout.key_id,
        currency: checkout.currency ?? 'INR',
        name: 'MeeSell',
        description: `${checkout.tier} subscription`,
        // Recurring tiers use subscription_id; LTD uses order_id + amount.
        ...(checkout.razorpay_subscription_id
          ? { subscription_id: checkout.razorpay_subscription_id }
          : {}),
        ...(checkout.razorpay_order_id
          ? {
              order_id: checkout.razorpay_order_id,
              amount: checkout.amount_paise ?? undefined,
            }
          : {}),
        /**
         * handler: fired when the user completes the payment flow.
         * This is NOT the source of truth for the plan grant — it means
         * "payment submitted to Razorpay". The actual grant is webhook-driven.
         * Transition: payment_submitted → PENDING → poll.
         */
        handler: (_response: unknown) => {
          paymentSubmitted = true;
          resolve({ status: 'payment_submitted' });
        },
        modal: {
          /**
           * ondismiss: fired when the modal is closed by the user.
           * Two cases:
           *   - paymentSubmitted=true: handler already resolved, this is a no-op.
           *   - paymentSubmitted=false: user backed out without paying → cancelled.
           */
          ondismiss: () => {
            if (!paymentSubmitted) {
              resolve({ status: 'cancelled' });
            }
          },
          // Prevent the modal from auto-closing on escape before payment
          // (the user must explicitly close it).
          escape: false,
          backdropclose: false,
        },
        // Theme — matches MeeSell brand (primary orange)
        theme: { color: '#F26B23' },
      };

      const rzp = new RazorpayConstructor(options);
      rzp.open();
    });
  }

  private _fallbackToShortUrl(checkout: BillingCheckout): Promise<CheckoutResult> {
    if (checkout.short_url) {
      window.open(checkout.short_url, '_blank', 'noopener,noreferrer');
      // Treat as pending — user may have completed payment in the new tab.
      return Promise.resolve({ status: 'short_url_opened' });
    }
    // No widget, no short_url — surface as cancelled (component shows retry).
    return Promise.resolve({ status: 'cancelled' });
  }
}
