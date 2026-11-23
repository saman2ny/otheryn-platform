import { ContentPlatform } from './content.model';

export type CalendarEventStatus = 'scheduled' | 'published' | 'missed';

export interface CalendarEvent {
  id: string;
  contentId: string;
  title: string;
  platform: ContentPlatform;
  scheduledAt: string;
  status: CalendarEventStatus;
}

export interface CreateCalendarEventRequest {
  contentId: string;
  title: string;
  platform: ContentPlatform;
  scheduledAt: string;
}
