/**
 * Sync Analytics Service
 * Phase 5, Task 5.6
 * Service methods for sync analytics API calls
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8181/api';

export interface SyncOperation {
  id: string;
  trigger: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  files_processed: number;
  chunks_added: number;
  chunks_modified: number;
  chunks_deleted: number;
  duration_seconds: number | null;
  error_message: string | null;
}

export interface PerformanceMetrics {
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  average_duration: number;
  total_files_processed: number;
  total_chunks_added: number;
  total_chunks_modified: number;
  total_chunks_deleted: number;
  success_rate: number;
  syncs_by_trigger: Record<string, number>;
}

export interface ErrorStatistics {
  total_errors: number;
  error_rate: number;
  errors_by_trigger: Record<string, number>;
  common_errors: Array<{
    message: string;
    count: number;
  }>;
}

export interface GrowthByDate {
  date: string;
  files_processed: number;
  chunks_added: number;
  chunks_modified: number;
  chunks_deleted: number;
  syncs_count: number;
}

export interface GrowthMetrics {
  growth_by_date: GrowthByDate[];
  cumulative_files: number;
  cumulative_chunks: number;
}

export interface SyncHistoryResponse {
  project_id: string;
  days: number;
  operations: SyncOperation[];
}

export interface PerformanceResponse {
  project_id: string;
  days: number;
  metrics: PerformanceMetrics;
}

export interface ErrorStatisticsResponse {
  project_id: string;
  days: number;
  statistics: ErrorStatistics;
}

export interface GrowthMetricsResponse {
  project_id: string;
  days: number;
  metrics: GrowthMetrics;
}

/**
 * Get sync operation history for a project
 */
export async function getSyncHistory(
  projectId: string,
  days: number = 30
): Promise<SyncHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/analytics/sync-history?days=${days}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch sync history' }));
    throw new Error(error.detail || 'Failed to fetch sync history');
  }

  return response.json();
}

/**
 * Get performance metrics for a project
 */
export async function getPerformanceMetrics(
  projectId: string,
  days: number = 30
): Promise<PerformanceResponse> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/analytics/performance?days=${days}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch performance metrics' }));
    throw new Error(error.detail || 'Failed to fetch performance metrics');
  }

  return response.json();
}

/**
 * Get error statistics for a project
 */
export async function getErrorStatistics(
  projectId: string,
  days: number = 30
): Promise<ErrorStatisticsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/analytics/errors?days=${days}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch error statistics' }));
    throw new Error(error.detail || 'Failed to fetch error statistics');
  }

  return response.json();
}

/**
 * Get growth metrics for a project
 */
export async function getGrowthMetrics(
  projectId: string,
  days: number = 30
): Promise<GrowthMetricsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/analytics/growth?days=${days}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch growth metrics' }));
    throw new Error(error.detail || 'Failed to fetch growth metrics');
  }

  return response.json();
}

// Export as part of syncAnalyticsService
export const syncAnalyticsService = {
  getSyncHistory,
  getPerformanceMetrics,
  getErrorStatistics,
  getGrowthMetrics
};
