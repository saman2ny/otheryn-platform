import { Component, input } from '@angular/core';

@Component({
  selector: 'dp-page-header',
  templateUrl: './page-header.html',
})
export class PageHeader {
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
}
