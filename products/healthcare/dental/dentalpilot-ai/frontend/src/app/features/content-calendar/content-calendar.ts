import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, finalize, of } from 'rxjs';
import { CalendarEvent } from '../../core/models/calendar.model';
import { GeneratedContent } from '../../core/models/content.model';
import { NotificationService } from '../../core/services/notification.service';
import { ContentGeneratorService } from '../content-generator/content-generator.service';
import { formFieldClass } from '../../shared/forms/form-field-class';
import { EmptyState } from '../../shared/ui/empty-state/empty-state';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { ContentCalendarService } from './content-calendar.service';

@Component({
  selector: 'dp-content-calendar',
  imports: [ReactiveFormsModule, PageHeader, EmptyState, DatePipe],
  templateUrl: './content-calendar.html',
})
export class ContentCalendar {
  protected readonly inputClass = formFieldClass;

  private readonly fb = inject(FormBuilder);
  private readonly calendarService = inject(ContentCalendarService);
  private readonly contentGeneratorService = inject(ContentGeneratorService);
  private readonly notifications = inject(NotificationService);

  protected readonly loading = signal(true);
  protected readonly scheduling = signal(false);
  protected readonly events = signal<CalendarEvent[]>([]);
  protected readonly availableContent = signal<GeneratedContent[]>([]);

  protected readonly sortedEvents = computed(() =>
    [...this.events()].sort(
      (a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime(),
    ),
  );

  protected readonly form = this.fb.nonNullable.group({
    contentId: ['', Validators.required],
    scheduledAt: ['', Validators.required],
  });

  constructor() {
    this.calendarService
      .list()
      .pipe(
        catchError(() => of([])),
        finalize(() => this.loading.set(false)),
      )
      .subscribe((events) => this.events.set(events));

    this.contentGeneratorService
      .list()
      .pipe(catchError(() => of([])))
      .subscribe((items) => this.availableContent.set(items));
  }

  protected schedule(): void {
    if (this.form.invalid || this.scheduling()) {
      this.form.markAllAsTouched();
      return;
    }

    const { contentId, scheduledAt } = this.form.getRawValue();
    const content = this.availableContent().find((item) => item.id === contentId);
    if (!content) {
      return;
    }

    this.scheduling.set(true);
    this.calendarService
      .create({ contentId, scheduledAt, title: content.headline, platform: content.platform })
      .pipe(finalize(() => this.scheduling.set(false)))
      .subscribe({
        next: (event) => {
          this.events.update((items) => [...items, event]);
          this.form.reset();
          this.notifications.success('Post scheduled.');
        },
      });
  }

  protected removeEvent(id: string): void {
    this.calendarService.remove(id).subscribe({
      next: () => this.events.update((items) => items.filter((item) => item.id !== id)),
    });
  }
}
