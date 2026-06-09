# DatePicker

**Import:** `import { DatePicker } from 'primeng/datepicker'`
**Selector:** `p-datePicker`, `p-datepicker`, `p-date-picker`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| inputId | `string \| undefined` | undefined | ID of the inner input element |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| dateFormat | `string \| undefined` | locale default | Date format string (e.g. `'dd/mm/yy'`) |
| inline | `boolean` | false | Display as inline calendar (no popup) |
| showIcon | `boolean \| undefined` | undefined | Show calendar icon button next to input |
| showButtonBar | `boolean` | false | Show Today and Clear buttons |
| showTime | `boolean` | false | Whether to display a timepicker |
| timeOnly | `boolean` | false | Display only the timepicker |
| hourFormat | `'12' \| '24'` | `'24'` | Hour format for time display |
| selectionMode | `'single' \| 'multiple' \| 'range'` | `'single'` | Selection mode |
| disabled | `boolean` | false | Disables the component |
| minDate | `Date \| undefined` | undefined | Minimum selectable date |
| maxDate | `Date \| undefined` | undefined | Maximum selectable date |
| disabledDates | `Date[]` | undefined | Array of dates to disable |
| disabledDays | `number[]` | undefined | Array of day-of-week indices to disable (0=Sunday) |
| view | `'date' \| 'month' \| 'year'` | `'date'` | Picker view mode |
| inputStyle | `object \| null` | undefined | Inline style for input |
| inputStyleClass | `string \| undefined` | undefined | CSS class for input |
| styleClass | `string \| undefined` | undefined | CSS class for component |
| ariaLabel | `string \| undefined` | undefined | ARIA label |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onSelect | `EventEmitter<Date>` | Emitted on date selection |
| onChange | `EventEmitter<DatePickerChangeEvent>` | Emitted on value change |
| onInput | `EventEmitter<any>` | Emitted when typing |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |
| onClose | `EventEmitter<HTMLElement>` | Emitted when panel closes |
| onMonthChange | `EventEmitter<DatePickerMonthChangeEvent>` | Emitted on month navigation |
| onYearChange | `EventEmitter<DatePickerYearChangeEvent>` | Emitted on year navigation |
| onTodayClick | `EventEmitter<Date>` | Emitted when Today button clicked |
| onClear | `EventEmitter<any>` | Emitted when value cleared |

## Usage Example (from Sakai-ng)

```html
<!-- Basic datepicker with icon and button bar -->
<p-datepicker [showIcon]="true" [showButtonBar]="true" [(ngModel)]="calendarValue"></p-datepicker>

<!-- Reactive form binding -->
<p-datepicker formControlName="birthDate" dateFormat="dd/mm/yy" [showIcon]="true"></p-datepicker>

<!-- Date range picker -->
<p-datepicker [(ngModel)]="rangeDates" selectionMode="range" dateFormat="dd/mm/yy"></p-datepicker>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `dateFormat` uses pattern: `d`=day, `dd`=2-digit day, `mm`=month, `yy`=4-digit year.
- For Indian date format: use `dateFormat="dd/mm/yy"`.
