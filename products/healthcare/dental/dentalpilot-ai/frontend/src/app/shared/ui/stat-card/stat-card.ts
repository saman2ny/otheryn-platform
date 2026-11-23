import { Component, input } from '@angular/core';

@Component({
  selector: 'dp-stat-card',
  templateUrl: './stat-card.html',
})
export class StatCard {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly hint = input('');
  readonly icon = input<string>('');
}
