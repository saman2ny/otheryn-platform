import { Component, inject } from '@angular/core';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'dp-toast-container',
  templateUrl: './toast-container.html',
})
export class ToastContainer {
  protected readonly notifications = inject(NotificationService);
}
