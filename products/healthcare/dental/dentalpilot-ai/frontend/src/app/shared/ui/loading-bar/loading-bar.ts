import { Component, inject } from '@angular/core';
import { LoadingService } from '../../../core/services/loading.service';

@Component({
  selector: 'dp-loading-bar',
  templateUrl: './loading-bar.html',
})
export class LoadingBar {
  protected readonly loading = inject(LoadingService);
}
