export type ExportFormat = 'pdf' | 'png' | 'csv';

export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ExportRequest {
  contentIds: string[];
  format: ExportFormat;
}

export interface ExportJob {
  id: string;
  format: ExportFormat;
  status: ExportStatus;
  contentIds: string[];
  downloadUrl?: string;
  createdAt: string;
}
