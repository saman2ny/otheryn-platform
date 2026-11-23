import { Injectable, signal } from '@angular/core';

export type NotificationKind = 'success' | 'error' | 'info';

export interface Notification {
  id: number;
  kind: NotificationKind;
  message: string;
}

const DEFAULT_DURATION_MS = 5000;

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly nextId = signal(0);
  readonly notifications = signal<Notification[]>([]);

  success(message: string): void {
    this.push('success', message);
  }

  error(message: string): void {
    this.push('error', message);
  }

  info(message: string): void {
    this.push('info', message);
  }

  dismiss(id: number): void {
    this.notifications.update((items) => items.filter((item) => item.id !== id));
  }

  private push(kind: NotificationKind, message: string): void {
    const id = this.nextId() + 1;
    this.nextId.set(id);
    this.notifications.update((items) => [...items, { id, kind, message }]);
    setTimeout(() => this.dismiss(id), DEFAULT_DURATION_MS);
  }
}
