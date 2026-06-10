# Stepper

**Import:** `import { Stepper, StepList, Step, StepPanels, StepPanel, StepItem, StepperSeparator } from 'primeng/stepper'`
**Selector:** `p-stepper` (root), `p-step-list`, `p-step`, `p-step-panels`, `p-step-panel`, `p-step-item`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Composable API — similar to Accordion. Use nested sub-components rather than a single flat API.

## Stepper @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `ModelSignal<number \| undefined>` | undefined | Active step value (signal two-way binding) |
| linear | (signal) `boolean` | false | When true, steps must be completed in order |
| transitionOptions | (signal) | — | Transition config |
| motionOptions | (signal) | — | Animation config |

## Step @Input() Props

| Prop | Type | Description |
|------|------|-------------|
| value | `ModelSignal<number \| undefined>` | This step's numeric value/index |
| disabled | (signal) `boolean` | Disables this step |

## Usage Example

```html
<!-- Composable stepper -->
<p-stepper [(value)]="activeStep">
  <p-step-list>
    <p-step [value]="1">Step 1 - Details</p-step>
    <p-step [value]="2">Step 2 - Images</p-step>
    <p-step [value]="3">Step 3 - Pricing</p-step>
  </p-step-list>
  <p-step-panels>
    <p-step-panel [value]="1">
      <ng-template pTemplate="content" let-activateCallback="activateCallback">
        <!-- Step 1 content -->
        <p-button label="Next" (onClick)="activateCallback(2)" />
      </ng-template>
    </p-step-panel>
    <p-step-panel [value]="2">
      <ng-template pTemplate="content" let-activateCallback="activateCallback">
        <!-- Step 2 content -->
        <p-button label="Back" severity="secondary" (onClick)="activateCallback(1)" />
        <p-button label="Next" (onClick)="activateCallback(3)" />
      </ng-template>
    </p-step-panel>
    <p-step-panel [value]="3">
      <ng-template pTemplate="content">
        <!-- Step 3 content - final -->
      </ng-template>
    </p-step-panel>
  </p-step-panels>
</p-stepper>

<!-- In component -->
activeStep = signal<number>(1);
```

## Notes

- Signal-based two-way binding: `[(value)]="activeStep"` where `activeStep` is a `signal<number>`.
- If using plain variable: split to `[value]="activeStep()"` + `(valueChange)="activeStep.set($event)"`.
- `linear="true"` prevents skipping ahead — users must complete each step in order.
- Use `activateCallback` from the `pTemplate="content"` context to programmatically navigate between steps.
