// features/account/onboarding/onboarding.component.ts
// Mat-stepper shell for /onboarding — 3-step wizard skeleton.
//
// Dispatch 1: stepper structure, correct signals, navigation stubs, i18n keys.
// Dispatch 2: SuperCategoryChipsComponent (Phase 2 categories) + ComplianceStepComponent (Phase 3).
// Dispatch 3: OnboardingApiService wired to onSubmit() + real backend submission.

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
  ViewChild,
} from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoPipe } from '@jsverse/transloco';
import { SuperCategoryChipsComponent } from '../components/super-category-chips/super-category-chips.component';
import { ComplianceStepComponent, FieldSpec } from '../components/compliance-step/compliance-step.component';

@Component({
  selector: 'mee-onboarding-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterModule,
    MatStepperModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    TranslocoPipe,
    SuperCategoryChipsComponent,
    ComplianceStepComponent,
  ],
  template: `
    <div class="min-h-screen bg-bg flex items-center justify-center p-4">
      <div class="w-full max-w-2xl bg-surface rounded-mee-lg shadow-mee-2">

        <div class="p-6 border-b border-outline">
          <h1 class="text-mee-2xl font-bold text-on-surface">
            {{ 'onboarding.title' | transloco }}
          </h1>
        </div>

        <mat-stepper [linear]="false" #stepper class="mee-onboarding-stepper">

          <!-- STEP 1: Business Details -->
          <mat-step [completed]="phase1Submitted()">
            <ng-template matStepLabel>
              {{ 'onboarding.steps.businessDetails' | transloco }}
            </ng-template>
            <div class="p-4 sm:p-6">
              <p class="text-mee-lg font-semibold text-on-surface mb-2">
                {{ 'onboarding.phase1.title' | transloco }}
              </p>
              <p class="text-mee-sm text-on-surface-variant mb-6">
                {{ 'onboarding.phase1.help' | transloco }}
              </p>
              <!-- Phase 1 form fields land in a future dispatch -->
              <div class="h-32 rounded-mee-md bg-surface-variant flex items-center justify-center text-mee-sm text-on-surface-variant">
                {{ 'onboarding.phase1.placeholder' | transloco }}
              </div>
            </div>
            <div class="flex justify-end gap-2 px-4 pb-4">
              <button mat-flat-button color="primary" (click)="onPhase1Next()">
                {{ 'onboarding.actions.next' | transloco }}
              </button>
            </div>
          </mat-step>

          <!-- STEP 2: Product Categories -->
          <mat-step [completed]="phase2Submitted()">
            <ng-template matStepLabel>
              {{ 'onboarding.steps.productCategories' | transloco }}
            </ng-template>
            <div class="p-4 sm:p-6">
              <p class="text-mee-lg font-semibold text-on-surface mb-2">
                {{ 'onboarding.phase2.title' | transloco }}
              </p>
              <p class="text-mee-sm text-on-surface-variant mb-6">
                {{ 'onboarding.phase2.help' | transloco }}
              </p>
              <mee-super-category-chips
                (selectionChange)="selectedSuperCategories.set($event)">
              </mee-super-category-chips>
            </div>
            <div class="flex justify-between gap-2 px-4 pb-4">
              <button mat-stroked-button matStepperPrevious>
                {{ 'onboarding.actions.back' | transloco }}
              </button>
              <button mat-flat-button color="primary" (click)="onPhase2Next()">
                {{ 'onboarding.actions.next' | transloco }}
              </button>
            </div>
          </mat-step>

          <!-- STEP 3: Compliance -->
          <mat-step>
            <ng-template matStepLabel>
              {{ 'onboarding.steps.compliance' | transloco }}
            </ng-template>
            <div class="p-4 sm:p-6">
              <p class="text-mee-lg font-semibold text-on-surface mb-2">
                {{ 'onboarding.phase3.title' | transloco }}
              </p>
              <p class="text-mee-sm text-on-surface-variant mb-6">
                {{ 'onboarding.phase3.help' | transloco }}
              </p>
              @if (selectedSuperCategories().length === 0) {
                <div class="rounded-mee-md bg-surface-variant flex items-center justify-center p-6 text-mee-sm text-on-surface-variant">
                  {{ 'onboarding.phase3.noCategories' | transloco }}
                </div>
              } @else {
                <div class="space-y-6">
                  @for (id of selectedSuperCategories(); track id) {
                    <div class="rounded-mee-md border border-outline p-4">
                      <mee-compliance-step
                        [superCategoryId]="id"
                        [fields]="complianceFields()[id] ?? []"
                        [saving]="saving()"
                        (formSubmit)="onComplianceSubmit(id, $event)"
                        (formBack)="stepper.previous()">
                      </mee-compliance-step>
                    </div>
                  }
                </div>
              }
            </div>
            <div class="flex justify-between gap-2 px-4 pb-4">
              <button mat-stroked-button matStepperPrevious>
                {{ 'onboarding.actions.back' | transloco }}
              </button>
              <button mat-flat-button color="primary" (click)="onSubmit()" [disabled]="saving()">
                @if (saving()) {
                  <mat-spinner diameter="16" class="inline-block mr-2"></mat-spinner>
                }
                {{ 'onboarding.actions.completeSetup' | transloco }}
              </button>
            </div>
          </mat-step>

        </mat-stepper>

      </div>
    </div>
  `,
})
export class OnboardingWizardComponent {
  private readonly router = inject(Router);

  @ViewChild('stepper') stepper!: MatStepper;

  // Component-local reactive state
  readonly loading = signal(false);  // future: true while fetching required-fields
  readonly saving  = signal(false);  // true while submitting Phase 3

  readonly selectedSuperCategories = signal<string[]>([]); // Phase 2 output
  readonly phase1Submitted = signal(false); // set true when Phase 1 Next is clicked (stub)
  readonly phase2Submitted = signal(false); // set true when Phase 2 Next is clicked (stub)

  // Keyed by super_id. Populated from onboarding-api.service.ts in the next dispatch.
  // Empty for now — compliance steps render with no fields until the API service lands.
  readonly complianceFields = signal<Record<string, FieldSpec[]>>({});

  onPhase1Next(): void {
    this.phase1Submitted.set(true);
    this.stepper?.next();
  }

  onPhase2Next(): void {
    this.phase2Submitted.set(true);
    this.stepper?.next();
  }

  onComplianceSubmit(superCategoryId: string, values: Record<string, string | null>): void {
    // TODO(dispatch-4): call onboardingApiService.patchCompliance(superCategoryId, values)
    console.debug('[onboarding] compliance submitted for', superCategoryId, values);
  }

  onSubmit(): void {
    this.saving.set(true);
    // TODO(dispatch-4): replace with onboardingApiService.submitCompliance() chain
    setTimeout(() => {
      this.saving.set(false);
      this.router.navigateByUrl('/dashboard');
    }, 300);
  }
}
