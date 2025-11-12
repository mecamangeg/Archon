/**
 * Projects Service Sync Extensions
 * Phase 1, Task 1.4
 * Service methods for project sync API calls
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8181/api';

export interface SyncConfig {
  local_path?: string | null;
  sync_mode?: string;
  auto_sync_enabled?: boolean;
}

export interface SyncStatus {
  project_id: string;
  sync_status: string;
  last_sync_at: string | null;
  auto_sync_enabled: boolean;
  sync_mode: string;
  local_path: string | null;
  last_sync_error: string | null;
  stats: {
    total_files: number;
    total_chunks: number;
    last_sync_duration_seconds: number;
  };
}

export interface TriggerSyncOptions {
  trigger: string;
  changed_files?: string[];
}

export interface TriggerSyncResponse {
  success: boolean;
  sync_job_id: string;
  status: string;
  message?: string;
  trigger: string;
  stats?: any;
}

/**
 * Get sync status for a project
 */
export async function getSyncStatus(projectId: string): Promise<SyncStatus> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/sync/status`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch sync status' }));
    throw new Error(error.detail || 'Failed to fetch sync status');
  }

  return response.json();
}

/**
 * Update sync configuration for a project
 */
export async function updateSyncConfig(
  projectId: string,
  config: SyncConfig
): Promise<{ success: boolean; project_id: string; config: any }> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/sync/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update sync config' }));
    throw new Error(error.detail || 'Failed to update sync config');
  }

  return response.json();
}

/**
 * Trigger manual sync for a project
 */
export async function triggerSync(
  projectId: string,
  options: TriggerSyncOptions
): Promise<TriggerSyncResponse> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options)
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to trigger sync' }));
    throw new Error(error.detail || 'Failed to trigger sync');
  }

  return response.json();
}

// Export as part of projectsService
export const projectsSyncService = {
  getSyncStatus,
  updateSyncConfig,
  triggerSync
};
