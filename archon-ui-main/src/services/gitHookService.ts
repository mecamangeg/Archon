/**
 * Git Hook Service
 * Phase 4, Task 4.4
 * Service methods for git hook API calls
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8181/api';

export interface GitHookStatus {
  project_id: string;
  installed: boolean;
  hook_path: string | null;
  is_git_repo: boolean;
  metadata?: {
    size_bytes: number;
    modified_at: string;
  };
  reason?: string;
}

export interface InstallGitHookOptions {
  preserve_existing?: boolean;
}

export interface UninstallGitHookOptions {
  restore_backup?: boolean;
}

export interface InstallGitHookResponse {
  success: boolean;
  project_id: string;
  message: string;
  hook_path: string;
}

export interface UninstallGitHookResponse {
  success: boolean;
  project_id: string;
  message: string;
  backup_restored: boolean;
}

/**
 * Install git hook for a project
 */
export async function installGitHook(
  projectId: string,
  options?: InstallGitHookOptions
): Promise<InstallGitHookResponse> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/git-hook/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options || {})
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to install git hook' }));
    throw new Error(error.detail || 'Failed to install git hook');
  }

  return response.json();
}

/**
 * Uninstall git hook for a project
 */
export async function uninstallGitHook(
  projectId: string,
  options?: UninstallGitHookOptions
): Promise<UninstallGitHookResponse> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/git-hook/uninstall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options || {})
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to uninstall git hook' }));
    throw new Error(error.detail || 'Failed to uninstall git hook');
  }

  return response.json();
}

/**
 * Get git hook status for a project
 */
export async function getGitHookStatus(projectId: string): Promise<GitHookStatus> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/git-hook/status`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch git hook status' }));
    throw new Error(error.detail || 'Failed to fetch git hook status');
  }

  return response.json();
}

// Export as part of gitHookService
export const gitHookService = {
  installGitHook,
  uninstallGitHook,
  getGitHookStatus
};
