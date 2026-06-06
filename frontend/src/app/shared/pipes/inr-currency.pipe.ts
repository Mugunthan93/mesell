// shared/pipes/inr-currency.pipe.ts
// Indian numbering format with ₹ prefix — 1499 → ₹1,499; 149900 → ₹1,49,900

import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'inrCurrency',
  standalone: true,
  pure: true,
})
export class InrCurrencyPipe implements PipeTransform {
  /**
   * Formats a number using the Indian numbering system with ₹ prefix.
   * Uses Intl.NumberFormat with locale 'en-IN' for correct lakh/crore grouping.
   */
  transform(value: number | string | null | undefined): string {
    if (value === null || value === undefined || value === '') return '';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(num);
  }
}
