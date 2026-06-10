import {
  ChangeDetectionStrategy,
  Component,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { MeeButtonComponent } from '../../ui';

@Component({
  selector: 'app-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'mee-landing' },
  imports: [RouterLink, MeeButtonComponent],
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background-color: var(--mee-color-bg);
      color: var(--mee-color-on-surface);
      font-family: 'Plus Jakarta Sans', Inter, sans-serif;
      scroll-behavior: smooth;
    }

    /* NAV */
    .nav-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      background-color: var(--mee-color-surface);
      border-bottom: 1px solid var(--mee-color-outline);
      position: sticky;
      top: 0;
      z-index: 10;
    }

    .logo {
      font-size: 20px;
      font-weight: 800;
      color: var(--mee-color-primary);
      text-decoration: none;
      letter-spacing: -0.5px;
    }

    /* PRIMARY BUTTON LINK */
    .btn-primary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 10px 24px;
      border-radius: var(--mee-radius-md, 8px);
      background-color: var(--mee-color-primary);
      color: var(--mee-color-on-primary, #fff);
      font-weight: 600;
      font-size: 15px;
      text-decoration: none;
      cursor: pointer;
      transition: opacity 0.15s ease;
    }

    .btn-primary:hover {
      opacity: 0.9;
    }

    .btn-primary-lg {
      padding: 14px 32px;
      font-size: 17px;
      border-radius: var(--mee-radius-md, 8px);
    }

    /* HERO */
    .hero-section {
      padding: 48px 20px 40px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 20px;
    }

    .hero-headline {
      font-size: 32px;
      font-weight: 800;
      line-height: 1.2;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    .hero-subtitle {
      font-size: 16px;
      line-height: 1.6;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
      max-width: 480px;
    }

    .hero-actions {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }

    /* HOW IT WORKS */
    .how-section {
      padding: 48px 20px;
      background-color: var(--mee-color-surface);
    }

    .section-headline {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 32px;
    }

    .steps-list {
      display: flex;
      flex-direction: column;
      gap: 24px;
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .step-item {
      display: flex;
      align-items: flex-start;
      gap: 16px;
    }

    .step-number {
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 40px;
      min-height: 40px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background-color: var(--mee-color-primary);
      color: var(--mee-color-on-primary, #fff);
      font-weight: 700;
      font-size: 16px;
      flex-shrink: 0;
    }

    .step-content {
      padding-top: 8px;
    }

    .step-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0 0 4px;
    }

    .step-desc {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    /* FOOTER */
    .footer-section {
      padding: 40px 20px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }

    .pricing-note {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    .footer-actions {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }

    .login-link {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      font-size: 14px;
      color: var(--mee-color-primary);
      text-decoration: none;
      font-weight: 500;
    }

    .login-link:hover {
      text-decoration: underline;
    }

    .copyright {
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
      margin: 8px 0 0;
    }

    /* see-how link */
    .see-how-link {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      font-size: 15px;
      color: var(--mee-color-on-surface-muted);
      text-decoration: none;
      font-weight: 500;
    }

    .see-how-link:hover {
      color: var(--mee-color-primary);
    }

    /* DESKTOP — 768px+ */
    @media (min-width: 768px) {
      .nav-bar {
        padding: 16px 40px;
      }

      .hero-section {
        padding: 72px 40px 56px;
      }

      .hero-headline {
        font-size: 44px;
      }

      .hero-actions {
        flex-direction: row;
        width: auto;
        align-items: center;
      }

      .how-section {
        padding: 64px 40px;
      }

      .footer-section {
        padding: 48px 40px;
      }

      .footer-actions {
        flex-direction: row;
        width: auto;
        align-items: center;
      }
    }

    /* WIDE — 1280px+ */
    @media (min-width: 1280px) {
      .nav-bar {
        padding: 16px 80px;
      }

      .hero-section {
        padding: 96px 80px 72px;
        max-width: 640px;
      }

      .hero-headline {
        font-size: 52px;
      }

      .how-section {
        padding: 80px;
      }

      .steps-list {
        flex-direction: row;
        gap: 40px;
      }

      .step-item {
        flex: 1;
        flex-direction: column;
        align-items: flex-start;
      }

      .step-content {
        padding-top: 0;
      }

      .footer-section {
        padding: 64px 80px;
      }
    }
  `],
  template: `
    <header>
      <nav class="nav-bar" aria-label="Main navigation">
        <span class="logo" aria-label="MeeSell">MeeSell</span>
        <a routerLink="/login" class="login-link" aria-label="Log in to MeeSell">
          <mee-button variant="ghost" size="sm" label="Log in" />
        </a>
      </nav>
    </header>

    <section aria-labelledby="hero-headline" class="hero-section">
      <h1 id="hero-headline" class="hero-headline">
        Create a Meesho catalog<br>in 3 minutes.
      </h1>
      <p class="hero-subtitle">
        AI fills your form. We check your images.
        You download the XLSX. Zero Meesho rejections.
      </p>
      <div class="hero-actions">
        <a
          routerLink="/signup"
          class="btn-primary btn-primary-lg"
          aria-label="Start free — create your first Meesho catalog"
        >
          Start free &rarr;
        </a>
        <a
          href="#how"
          class="see-how-link"
          aria-label="See how MeeSell works"
        >
          See how it works
        </a>
      </div>
    </section>

    <section
      id="how"
      aria-labelledby="how-headline"
      class="how-section"
    >
      <h2 id="how-headline" class="section-headline">How it works</h2>
      <ol class="steps-list">
        <li class="step-item">
          <span class="step-number" aria-hidden="true">1</span>
          <div class="step-content">
            <p class="step-title">Pick your category</p>
            <p class="step-desc">
              Describe your product and our AI suggests the best
              Meesho category for your listing.
            </p>
          </div>
        </li>
        <li class="step-item">
          <span class="step-number" aria-hidden="true">2</span>
          <div class="step-content">
            <p class="step-title">AI fills your fields</p>
            <p class="step-desc">
              One click and Gemini AI auto-populates your catalog
              form — title, description, attributes and more.
            </p>
          </div>
        </li>
        <li class="step-item">
          <span class="step-number" aria-hidden="true">3</span>
          <div class="step-content">
            <p class="step-title">Download the XLSX</p>
            <p class="step-desc">
              Export your ready-to-upload Meesho catalog file.
              Images pre-checked, pricing optimised.
            </p>
          </div>
        </li>
      </ol>
    </section>

    <footer>
      <div class="footer-section">
        <p class="pricing-note">&#8377;499/month &middot; Cancel anytime &middot; No credit card for trial</p>
        <div class="footer-actions">
          <a
            routerLink="/signup"
            class="btn-primary"
            aria-label="Start free — create your Meesho catalog"
          >
            Start free &rarr;
          </a>
          <a routerLink="/login" class="login-link">Log in</a>
        </div>
        <p class="copyright">&copy; {{ currentYear() }} MeeSell. All rights reserved.</p>
      </div>
    </footer>
  `,
})
export class LandingComponent {
  readonly currentYear = signal(new Date().getFullYear());
}
