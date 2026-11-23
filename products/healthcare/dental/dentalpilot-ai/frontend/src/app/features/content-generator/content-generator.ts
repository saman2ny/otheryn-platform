import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, finalize, of } from 'rxjs';
import { ContentPlatform, ContentTone, GeneratedContent } from '../../core/models/content.model';
import { NotificationService } from '../../core/services/notification.service';
import { formFieldClass } from '../../shared/forms/form-field-class';
import { EmptyState } from '../../shared/ui/empty-state/empty-state';
import { PageHeader } from '../../shared/ui/page-header/page-header';
import { ContentGeneratorService } from './content-generator.service';

@Component({
  selector: 'dp-content-generator',
  imports: [ReactiveFormsModule, PageHeader, EmptyState],
  templateUrl: './content-generator.html',
})
export class ContentGenerator {
  protected readonly inputClass = formFieldClass;

  private readonly fb = inject(FormBuilder);
  private readonly contentGeneratorService = inject(ContentGeneratorService);
  private readonly notifications = inject(NotificationService);

  protected readonly generating = signal(false);
  protected readonly generatedItems = signal<GeneratedContent[]>([]);

  protected readonly form = this.fb.nonNullable.group({
    topic: ['', Validators.required],
    platform: ['instagram' as ContentPlatform, Validators.required],
    tone: ['friendly' as ContentTone, Validators.required],
    treatment: [''],
    includeHashtags: [true],
    includeCallToAction: [true],
  });

  constructor() {
    this.contentGeneratorService
      .list()
      .pipe(catchError(() => of([])))
      .subscribe((items) => this.generatedItems.set(items));
  }

  protected generate(): void {
    if (this.form.invalid || this.generating()) {
      this.form.markAllAsTouched();
      return;
    }

    this.generating.set(true);
    this.contentGeneratorService
      .generate(this.form.getRawValue())
      .pipe(finalize(() => this.generating.set(false)))
      .subscribe({
        next: (content) => {
          this.generatedItems.update((items) => [content, ...items]);
          this.notifications.success('Content generated.');
        },
      });
  }
}
