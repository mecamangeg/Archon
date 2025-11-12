/**
 * Watcher Service
 * Phase 3, Task 3.7
 * Service methods for watcher API calls
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8181/api';

export interface WatcherStatus {
  project_id: string;
  is_active: boolean;
  last_event_at: string | null;
  events_processed: number;
  error: string | null;
}

export interface WatcherHealth {
  status: string;
  worker_running: boolean;
  uptime_seconds: number;
  projects_watching: number;
  heartbeat_ago_seconds: number;
  cpu_percent: number;
  memory_mb: number;
}

export interface StartWatcherResponse {
  success: boolean;
  project_id: string;
  message: string;
}

export interface StopWatcherResponse {
  success: boolean;
  project_id: string;
  message: string;
}

/**
 * Start watcher for a project
 */
export async function startWatcher(projectId: string): Promise<StartWatcherResponse> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/watcher/start`, {
    method: 'POST'
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to start watcher' }));
    throw new Error(error.detail || 'Failed to start watcher');
  }

  return response.json();
}

/**
 * Stop watcher for a project
 */
export async function stopWatcher(projectId: string): Promise<StopWatcherResponse> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/watcher/stop`, {
    method: 'POST'
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to stop watcher' }));
    throw new Error(error.detail || 'Failed to stop watcher');
  }

  return response.json();
}

/**
 * Get watcher status for a project
 */
export async function getWatcherStatus(projectId: string): Promise<WatcherStatus> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/watcher/status`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch watcher status' }));
    throw new Error(error.detail || 'Failed to fetch watcher status');
  }

  return response.json();
}

/**
 * Get watcher health (global worker status)
 */
export async function getWatcherHealth(): Promise<WatcherHealth> {
  const response = await fetch(`${API_BASE_URL}/watcher/health`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch watcher health' }));
    throw new Error(error.detail || 'Failed to fetch watcher health');
  }

  return response.json();
}

// Export as part of watcherService
export const watcherService = {
  startWatcher,
  stopWatcher,
  getWatcherStatus,
  getWatcherHealth
};
