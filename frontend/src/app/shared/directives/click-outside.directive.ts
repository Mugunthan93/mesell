// shared/directives/click-outside.directive.ts
// Emits when a click occurs outside the host element per §5.E.2

import {
  Directive,
  ElementRef,
  EventEmitter,
  inject,
  OnDestroy,
  OnInit,
  Output,
} from '@angular/core';
import { fromEvent, Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';

@Directive({
  selector: '[meeClickOutside]',
  standalone: true,
})
export class ClickOutsideDirective implements OnInit, OnDestroy {
  @Output() readonly meeClickOutside = new EventEmitter<MouseEvent>();

  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private sub?: Subscription;

  ngOnInit(): void {
    // Listen on document — filter OUT clicks that are inside the host
    this.sub = fromEvent<MouseEvent>(document, 'click').pipe(
      filter(event => !this.el.nativeElement.contains(event.target as Node)),
    ).subscribe(event => this.meeClickOutside.emit(event));
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
