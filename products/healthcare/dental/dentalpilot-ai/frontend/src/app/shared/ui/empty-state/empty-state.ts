import { Component, input, output } from '@angular/core';

@Component({
  selector: 'dp-empty-state',
  templateUrl: './empty-state.html',
})
export class EmptyState {
  readonly icon = input('📋');
  readonly title = input.required<string>();
  readonly message = input('');
  readonly actionLabel = input('');
  readonly action = output<void>();
}
