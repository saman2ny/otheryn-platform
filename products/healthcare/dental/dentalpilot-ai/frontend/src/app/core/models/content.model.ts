export type ContentPlatform = 'instagram' | 'facebook' | 'google-business' | 'blog' | 'sms';

export type ContentTone = 'friendly' | 'professional' | 'premium' | 'playful' | 'educational';

export type ContentStatus = 'draft' | 'ready' | 'scheduled' | 'published';

export interface GenerateContentRequest {
  topic: string;
  platform: ContentPlatform;
  tone: ContentTone;
  treatment?: string;
  includeHashtags: boolean;
  includeCallToAction: boolean;
}

export interface GeneratedContent {
  id: string;
  platform: ContentPlatform;
  tone: ContentTone;
  topic: string;
  headline: string;
  body: string;
  hashtags: string[];
  imagePromptSuggestion?: string;
  status: ContentStatus;
  createdAt: string;
}
