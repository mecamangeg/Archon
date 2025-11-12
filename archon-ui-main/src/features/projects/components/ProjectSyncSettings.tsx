/**
 * Project Sync Settings Component
 * Phase 1, Task 1.4
 * Manages project codebase synchronization configuration
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Input,
  Switch,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  Badge
} from '@/components/ui';
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  FolderOpen,
  Activity,
  Power,
  PlayCircle,
  StopCircle,
  GitBranch
} from 'lucide-react';
import { projectsService } from '@/services/projectsService';
import { watcherService } from '@/services/watcherService';
import { gitHookService } from '@/services/gitHookService';
import type { Project } from '@/types';

interface ProjectSyncSettingsProps {
  projectId: string;
  onConfigUpdate?: () => void;
}

export const ProjectSyncSettings: React.FC<ProjectSyncSettingsProps> = ({
  projectId,
  onConfigUpdate
}) => {
  const queryClient = useQueryClient();

  // Fetch current sync status
  const { data: syncStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['project-sync-status', projectId],
    queryFn: () => projectsService.getSyncStatus(projectId),
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Fetch watcher status
  const { data: watcherStatus, isLoading: watcherLoading } = useQuery({
    queryKey: ['watcher-status', projectId],
    queryFn: () => watcherService.getWatcherStatus(projectId),
    refetchInterval: 10000, // Refresh every 10 seconds
    enabled: syncMode !== 'manual' && autoSyncEnabled
  });

  // Fetch git hook status
  const { data: gitHookStatus, isLoading: gitHookLoading } = useQuery({
    queryKey: ['git-hook-status', projectId],
    queryFn: () => gitHookService.getGitHookStatus(projectId),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: syncMode === 'git-hook'
  });

  // Local state
  const [localPath, setLocalPath] = useState(syncStatus?.local_path || '');
  const [syncMode, setSyncMode] = useState(syncStatus?.sync_mode || 'manual');
  const [autoSyncEnabled, setAutoSyncEnabled] = useState(syncStatus?.auto_sync_enabled || false);

  // Sync state from server when loaded
  useEffect(() => {
    if (syncStatus) {
      setLocalPath(syncStatus.local_path || '');
      setSyncMode(syncStatus.sync_mode || 'manual');
      setAutoSyncEnabled(syncStatus.auto_sync_enabled || false);
    }
  }, [syncStatus]);

  // Update config mutation
  const updateConfigMutation = useMutation({
    mutationFn: (config: any) => projectsService.updateSyncConfig(projectId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-sync-status', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onConfigUpdate?.();
      // Show success toast
      console.log('✅ Sync configuration updated');
    },
    onError: (error: any) => {
      console.error('Failed to update sync config:', error);
      // Show error toast
      alert(`Failed to update configuration: ${error.message}`);
    }
  });

  // Trigger sync mutation
  const triggerSyncMutation = useMutation({
    mutationFn: () => projectsService.triggerSync(projectId, { trigger: 'manual' }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['project-sync-status', projectId] });

      // Show success toast with stats
      const stats = data.stats;
      if (stats) {
        const message = `Sync completed: ${stats.files_processed} files, ${stats.chunks_added} chunks added`;
        console.log(`✅ ${message}. Duration: ${stats.duration_seconds}s`);
        // TODO: Replace with proper toast notification
        alert(`✅ ${message}\nDuration: ${stats.duration_seconds}s`);
      } else {
        console.log('✅ Sync triggered');
      }
    },
    onError: (error: any) => {
      console.error('Failed to trigger sync:', error);
      alert(`Failed to trigger sync: ${error.message}`);
    }
  });

  // Start watcher mutation
  const startWatcherMutation = useMutation({
    mutationFn: () => watcherService.startWatcher(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watcher-status', projectId] });
      console.log('✅ Watcher started');
      // TODO: Replace with proper toast notification
      alert('✅ Watcher started successfully');
    },
    onError: (error: any) => {
      console.error('Failed to start watcher:', error);
      alert(`Failed to start watcher: ${error.message}`);
    }
  });

  // Stop watcher mutation
  const stopWatcherMutation = useMutation({
    mutationFn: () => watcherService.stopWatcher(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watcher-status', projectId] });
      console.log('✅ Watcher stopped');
      // TODO: Replace with proper toast notification
      alert('✅ Watcher stopped successfully');
    },
    onError: (error: any) => {
      console.error('Failed to stop watcher:', error);
      alert(`Failed to stop watcher: ${error.message}`);
    }
  });

  // Install git hook mutation
  const installGitHookMutation = useMutation({
    mutationFn: () => gitHookService.installGitHook(projectId, { preserve_existing: true }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['git-hook-status', projectId] });
      console.log('✅ Git hook installed');
      // TODO: Replace with proper toast notification
      alert(`✅ Git hook installed successfully\nPath: ${data.hook_path}`);
    },
    onError: (error: any) => {
      console.error('Failed to install git hook:', error);
      alert(`Failed to install git hook: ${error.message}`);
    }
  });

  // Uninstall git hook mutation
  const uninstallGitHookMutation = useMutation({
    mutationFn: () => gitHookService.uninstallGitHook(projectId, { restore_backup: true }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['git-hook-status', projectId] });
      console.log('✅ Git hook uninstalled');
      const restoreMsg = data.backup_restored ? ' (backup restored)' : '';
      // TODO: Replace with proper toast notification
      alert(`✅ Git hook uninstalled successfully${restoreMsg}`);
    },
    onError: (error: any) => {
      console.error('Failed to uninstall git hook:', error);
      alert(`Failed to uninstall git hook: ${error.message}`);
    }
  });

  const handleSaveConfig = () => {
    updateConfigMutation.mutate({
      local_path: localPath || null,
      sync_mode: syncMode,
      auto_sync_enabled: autoSyncEnabled
    });
  };

  const handleTriggerSync = () => {
    if (!localPath) {
      alert('Please set a local path first');
      return;
    }
    triggerSyncMutation.mutate();
  };

  const handleStartWatcher = () => {
    if (!localPath) {
      alert('Please set a local path first');
      return;
    }
    if (!autoSyncEnabled) {
      alert('Please enable auto-sync first');
      return;
    }
    startWatcherMutation.mutate();
  };

  const handleStopWatcher = () => {
    stopWatcherMutation.mutate();
  };

  const handleInstallGitHook = () => {
    if (!localPath) {
      alert('Please set a local path first');
      return;
    }
    if (!gitHookStatus?.is_git_repo) {
      alert('Project path is not a git repository');
      return;
    }
    installGitHookMutation.mutate();
  };

  const handleUninstallGitHook = () => {
    if (window.confirm('Are you sure you want to uninstall the git hook? The backup will be restored if available.')) {
      uninstallGitHookMutation.mutate();
    }
  };

  const getSyncStatusBadge = () => {
    if (statusLoading) {
      return <Badge variant="secondary">Loading...</Badge>;
    }

    const status = syncStatus?.sync_status || 'never_synced';

    const statusConfig: Record<string, { label: string; icon: any; variant: any }> = {
      synced: { label: 'Synced', icon: CheckCircle, variant: 'success' },
      syncing: { label: 'Syncing...', icon: RefreshCw, variant: 'default' },
      error: { label: 'Error', icon: XCircle, variant: 'destructive' },
      never_synced: { label: 'Never Synced', icon: Clock, variant: 'secondary' }
    };

    const config = statusConfig[status] || statusConfig.never_synced;
    const Icon = config.icon;

    return (
      <Badge variant={config.variant}>
        <Icon className="w-3 h-3 mr-1" />
        {config.label}
      </Badge>
    );
  };

  const getWatcherStatusBadge = () => {
    if (watcherLoading) {
      return <Badge variant="secondary">Checking...</Badge>;
    }

    const isActive = watcherStatus?.is_active || false;

    if (isActive) {
      return (
        <Badge variant="success">
          <Activity className="w-3 h-3 mr-1 animate-pulse" />
          Watcher Active
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary">
          <Power className="w-3 h-3 mr-1" />
          Watcher Inactive
        </Badge>
      );
    }
  };

  const getGitHookStatusBadge = () => {
    if (gitHookLoading) {
      return <Badge variant="secondary">Checking...</Badge>;
    }

    const isInstalled = gitHookStatus?.installed || false;

    if (isInstalled) {
      return (
        <Badge variant="success">
          <GitBranch className="w-3 h-3 mr-1" />
          Git Hook Active
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary">
          <GitBranch className="w-3 h-3 mr-1" />
          Git Hook Inactive
        </Badge>
      );
    }
  };

  const hasChanges =
    localPath !== (syncStatus?.local_path || '') ||
    syncMode !== (syncStatus?.sync_mode || 'manual') ||
    autoSyncEnabled !== (syncStatus?.auto_sync_enabled || false);

  return (
    <div className="space-y-6 p-6 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Codebase Sync Settings
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Configure automatic synchronization of project codebase to knowledge base
          </p>
        </div>
        <div className="flex gap-2">
          {getSyncStatusBadge()}
          {syncMode !== 'manual' && syncMode !== 'git-hook' && autoSyncEnabled && getWatcherStatusBadge()}
          {syncMode === 'git-hook' && getGitHookStatusBadge()}
        </div>
      </div>

      {/* Error Display */}
      {syncStatus?.last_sync_error && syncStatus.sync_status === 'error' && (
        <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              Sync Error
            </p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">
              {syncStatus.last_sync_error}
            </p>
          </div>
        </div>
      )}

      {/* Local Path Input */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Local Project Path
        </label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="/path/to/your/project"
              className="pl-10"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Absolute path to the project directory on your local machine
        </p>
      </div>

      {/* Sync Mode Selector */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Sync Mode
        </label>
        <Select value={syncMode} onValueChange={setSyncMode}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">
              <div className="flex flex-col items-start">
                <span className="font-medium">Manual</span>
                <span className="text-xs text-gray-500">Sync only when you click the button</span>
              </div>
            </SelectItem>
            <SelectItem value="realtime">
              <div className="flex flex-col items-start">
                <span className="font-medium">Real-time</span>
                <span className="text-xs text-gray-500">Auto-sync on file changes</span>
              </div>
            </SelectItem>
            <SelectItem value="git-hook">
              <div className="flex flex-col items-start">
                <span className="font-medium">Git Hook</span>
                <span className="text-xs text-gray-500">Auto-sync on git commits</span>
              </div>
            </SelectItem>
            <SelectItem value="periodic">
              <div className="flex flex-col items-start">
                <span className="font-medium">Periodic</span>
                <span className="text-xs text-gray-500">Auto-sync every hour</span>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {syncMode === 'manual' && '✅ Click "Sync Now" to manually synchronize codebase'}
          {syncMode === 'realtime' && '🔄 Watches project directory for changes in real-time'}
          {syncMode === 'git-hook' && '📝 Syncs automatically after git commits'}
          {syncMode === 'periodic' && '⏰ Syncs every hour automatically'}
        </p>
      </div>

      {/* Auto-Sync Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div className="flex-1">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Enable Auto-Sync
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Automatically update knowledge base when files change
          </p>
        </div>
        <Switch
          checked={autoSyncEnabled}
          onCheckedChange={setAutoSyncEnabled}
          disabled={syncMode === 'manual'}
        />
      </div>

      {/* Last Sync Info */}
      {syncStatus?.last_sync_at && (
        <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
          <Clock className="w-4 h-4" />
          <span>
            Last synced: {new Date(syncStatus.last_sync_at).toLocaleString()}
          </span>
        </div>
      )}

      {/* Stats - Real-time from Phase 2 */}
      {syncStatus?.stats && syncStatus.stats.total_chunks > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Codebase Statistics
          </h4>
          <div className="grid grid-cols-3 gap-4 p-4 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700/50 dark:to-gray-800/50 rounded-lg">
            <div className="text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400">Files</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {syncStatus.stats.total_files.toLocaleString()}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400">Chunks</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {syncStatus.stats.total_chunks.toLocaleString()}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400">Duration</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {syncStatus.stats.last_sync_duration_seconds?.toFixed(1)}s
              </p>
            </div>
          </div>

          {/* Progress indicator during sync */}
          {syncStatus.sync_status === 'syncing' && (
            <div className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <RefreshCw className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Synchronizing codebase...
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                  This may take a few minutes for large projects
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Git Hook Controls */}
      {syncMode === 'git-hook' && (
        <div className="flex items-center gap-3 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
          <GitBranch className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-purple-800 dark:text-purple-200">
              Git Hook Controls
            </p>
            <p className="text-xs text-purple-600 dark:text-purple-300 mt-1">
              {gitHookStatus?.installed
                ? `Hook installed at: ${gitHookStatus.hook_path}`
                : gitHookStatus?.is_git_repo
                ? 'Install git hook to sync automatically on commits.'
                : 'Project path is not a git repository.'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleInstallGitHook}
              disabled={gitHookStatus?.installed || !gitHookStatus?.is_git_repo || installGitHookMutation.isPending}
              variant="default"
              size="sm"
            >
              {installGitHookMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Installing...
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Install Hook
                </>
              )}
            </Button>
            <Button
              onClick={handleUninstallGitHook}
              disabled={!gitHookStatus?.installed || uninstallGitHookMutation.isPending}
              variant="outline"
              size="sm"
            >
              {uninstallGitHookMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Uninstalling...
                </>
              ) : (
                <>
                  <StopCircle className="w-4 h-4 mr-2" />
                  Uninstall Hook
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Watcher Controls (Real-time and Periodic modes) */}
      {syncMode !== 'manual' && syncMode !== 'git-hook' && autoSyncEnabled && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
              File Watcher Controls
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
              {watcherStatus?.is_active
                ? `Watching for changes. ${watcherStatus.events_processed || 0} events processed.`
                : 'Start the file watcher to enable automatic sync.'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleStartWatcher}
              disabled={watcherStatus?.is_active || startWatcherMutation.isPending}
              variant="default"
              size="sm"
            >
              {startWatcherMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Start Watcher
                </>
              )}
            </Button>
            <Button
              onClick={handleStopWatcher}
              disabled={!watcherStatus?.is_active || stopWatcherMutation.isPending}
              variant="outline"
              size="sm"
            >
              {stopWatcherMutation.isPending ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Stopping...
                </>
              ) : (
                <>
                  <StopCircle className="w-4 h-4 mr-2" />
                  Stop Watcher
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button
          onClick={handleSaveConfig}
          disabled={!hasChanges || updateConfigMutation.isPending}
          variant="default"
        >
          {updateConfigMutation.isPending ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            'Save Configuration'
          )}
        </Button>

        <Button
          onClick={handleTriggerSync}
          disabled={!localPath || triggerSyncMutation.isPending}
          variant="secondary"
        >
          {triggerSyncMutation.isPending ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Syncing...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Sync Now
            </>
          )}
        </Button>
      </div>

      {/* Help Text for Git Hook */}
      {syncMode === 'git-hook' && !gitHookStatus?.is_git_repo && localPath && (
        <div className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Not a Git Repository
            </p>
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
              The configured local path is not a git repository. Initialize git in your project directory to use git-hook sync mode.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
