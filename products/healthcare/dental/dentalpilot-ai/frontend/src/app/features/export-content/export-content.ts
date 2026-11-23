import { DatePipe, UpperCasePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, finalize, of } from 'rxjs';
import { ExportFormat, ExportJob } from '../../core/models/export.model';
import { GeneratedContent } from '../../core/models/content.model';
import { NotificationService } from '../../core/services/notification.service';
import { ContentGeneratorService } from '../content-generator/content-generator.service';
import { formFieldClass } from '../../shared/forms/form-field-class';
import { EmptyState } from '../../shared/ui/empty-state/empty-state';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { ExportContentService } from './export-content.service';

@Component({
  selector: 'dp-export-content',
  imports: [ReactiveFormsModule, PageHeader, EmptyState, DatePipe, UpperCasePipe],
  templateUrl: './export-content.html',
})
export class ExportContent {
  protected readonly inputClass = formFieldClass;

  private readonly fb = inject(FormBuilder);
  private readonly exportService = inject(ExportContentService);
  private readonly contentGeneratorService = inject(ContentGeneratorService);
  private readonly notifications = inject(NotificationService);

  protected readonly submitting = signal(false);
  protected readonly availableContent = signal<GeneratedContent[]>([]);
  protected readonly jobs = signal<ExportJob[]>([]);
  protected readonly selectedIds = signal<Set<string>>(new Set());

  protected readonly form = this.fb.nonNullable.group({
    format: ['pdf' as ExportFormat, Validators.required],
  });

  constructor() {
    this.contentGeneratorService
      .list()
      .pipe(catchError(() => of([])))
      .subscribe((items) => this.availableContent.set(items));

    this.exportService
      .listJobs()
      .pipe(catchError(() => of([])))
      .subscribe((jobs) => this.jobs.set(jobs));
  }

  protected toggleSelection(id: string, checked: boolean): void {
    this.selectedIds.update((current) => {
      const next = new Set(current);
      checked ? next.add(id) : next.delete(id);
      return next;
    });
  }

  protected submitExport(): void {
    const contentIds = [...this.selectedIds()];
    if (!contentIds.length || this.submitting()) {
      return;
    }

    this.submitting.set(true);
    this.exportService
      .createJob({ contentIds, format: this.form.getRawValue().format })
      .pipe(finalize(() => this.submitting.set(false)))
      .subscribe({
        next: (job) => {
          this.jobs.update((items) => [job, ...items]);
          this.selectedIds.set(new Set());
          this.notifications.success(
            job.status === 'completed' ? 'Export ready.' : 'Export failed. Please try again.',
          );
        },
      });
  }

  protected download(jobId: string): void {
    this.exportService.download(jobId).subscribe({
      next: (response) => {
        const blob = response.body;
        if (!blob) {
          return;
        }
        const disposition = response.headers.get('content-disposition') ?? '';
        const match = /filename="?([^"]+)"?/.exec(disposition);
        const filename = match ? match[1] : `dentalpilot-export-${jobId.slice(0, 8)}`;

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.notifications.error('Unable to download this export.'),
    });
  }
}
