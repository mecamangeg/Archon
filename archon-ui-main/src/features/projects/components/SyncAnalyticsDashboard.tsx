/**
 * Sync Analytics Dashboard Component
 * Phase 5, Task 5.6
 * Displays sync performance metrics and trends
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Badge
} from '@/components/ui';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  FileText,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3
} from 'lucide-react';
import { syncAnalyticsService } from '@/services/syncAnalyticsService';

interface SyncAnalyticsDashboardProps {
  projectId: string;
}

export const SyncAnalyticsDashboard: React.FC<SyncAnalyticsDashboardProps> = ({
  projectId
}) => {
  const [timeRange, setTimeRange] = useState<number>(30);

  // Fetch performance metrics
  const { data: performanceData, isLoading: performanceLoading } = useQuery({
    queryKey: ['sync-performance', projectId, timeRange],
    queryFn: () => syncAnalyticsService.getPerformanceMetrics(projectId, timeRange),
    refetchInterval: 60000 // Refresh every minute
  });

  // Fetch error statistics
  const { data: errorData, isLoading: errorLoading } = useQuery({
    queryKey: ['sync-errors', projectId, timeRange],
    queryFn: () => syncAnalyticsService.getErrorStatistics(projectId, timeRange),
    refetchInterval: 60000
  });

  // Fetch growth metrics
  const { data: growthData, isLoading: growthLoading } = useQuery({
    queryKey: ['sync-growth', projectId, timeRange],
    queryFn: () => syncAnalyticsService.getGrowthMetrics(projectId, timeRange),
    refetchInterval: 60000
  });

  const performance = performanceData?.metrics;
  const errors = errorData?.statistics;
  const growth = growthData?.metrics;

  const isLoading = performanceLoading || errorLoading || growthLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Sync Analytics
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Performance metrics and trends for project synchronization
          </p>
        </div>

        {/* Time Range Selector */}
        <Select value={timeRange.toString()} onValueChange={(val) => setTimeRange(parseInt(val))}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="14">Last 14 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="60">Last 60 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Activity className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400" />
        </div>
      ) : (
        <>
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Syncs */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Syncs
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                      {performance?.total_syncs || 0}
                    </p>
                  </div>
                  <Activity className="w-10 h-10 text-blue-600 dark:text-blue-400" />
                </div>
              </CardContent>
            </Card>

            {/* Success Rate */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Success Rate
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <p className="text-3xl font-bold text-gray-900 dark:text-white">
                        {performance?.success_rate || 0}%
                      </p>
                      {performance && performance.success_rate >= 95 ? (
                        <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
                      ) : (
                        <TrendingDown className="w-6 h-6 text-red-600 dark:text-red-400" />
                      )}
                    </div>
                  </div>
                  <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
                </div>
              </CardContent>
            </Card>

            {/* Average Duration */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Avg Duration
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                      {performance?.average_duration?.toFixed(1) || 0}s
                    </p>
                  </div>
                  <Clock className="w-10 h-10 text-purple-600 dark:text-purple-400" />
                </div>
              </CardContent>
            </Card>

            {/* Files Processed */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Files Processed
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                      {performance?.total_files_processed?.toLocaleString() || 0}
                    </p>
                  </div>
                  <FileText className="w-10 h-10 text-orange-600 dark:text-orange-400" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sync Operations Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Sync Operations</CardTitle>
                <CardDescription>Breakdown by trigger type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Successful</p>
                      <p className="text-2xl font-semibold text-green-600 dark:text-green-400">
                        {performance?.successful_syncs || 0}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Failed</p>
                      <p className="text-2xl font-semibold text-red-600 dark:text-red-400">
                        {performance?.failed_syncs || 0}
                      </p>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      By Trigger Type
                    </p>
                    <div className="space-y-2">
                      {performance?.syncs_by_trigger && Object.entries(performance.syncs_by_trigger).map(([trigger, count]) => (
                        <div key={trigger} className="flex items-center justify-between">
                          <Badge variant="outline" className="capitalize">
                            {trigger}
                          </Badge>
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chunk Statistics */}
            <Card>
              <CardHeader>
                <CardTitle>Chunk Operations</CardTitle>
                <CardDescription>Total chunks processed</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div>
                      <p className="text-sm text-green-700 dark:text-green-300">Chunks Added</p>
                      <p className="text-2xl font-bold text-green-900 dark:text-green-100">
                        {performance?.total_chunks_added?.toLocaleString() || 0}
                      </p>
                    </div>
                    <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
                  </div>

                  <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div>
                      <p className="text-sm text-blue-700 dark:text-blue-300">Chunks Modified</p>
                      <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                        {performance?.total_chunks_modified?.toLocaleString() || 0}
                      </p>
                    </div>
                    <Activity className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                  </div>

                  <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <div>
                      <p className="text-sm text-red-700 dark:text-red-300">Chunks Deleted</p>
                      <p className="text-2xl font-bold text-red-900 dark:text-red-100">
                        {performance?.total_chunks_deleted?.toLocaleString() || 0}
                      </p>
                    </div>
                    <XCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Error Statistics */}
            {errors && errors.total_errors > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Error Statistics</CardTitle>
                  <CardDescription>Common errors and error rate</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                      <div>
                        <p className="text-sm text-red-700 dark:text-red-300">Error Rate</p>
                        <p className="text-3xl font-bold text-red-900 dark:text-red-100">
                          {errors.error_rate}%
                        </p>
                      </div>
                      <AlertCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
                    </div>

                    <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                        Common Errors
                      </p>
                      <div className="space-y-2">
                        {errors.common_errors.map((error, index) => (
                          <div key={index} className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-gray-800 rounded">
                            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-gray-700 dark:text-gray-300 truncate">
                                {error.message}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                Count: {error.count}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Growth Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Growth Overview</CardTitle>
                <CardDescription>Cumulative metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg">
                    <div>
                      <p className="text-sm text-blue-700 dark:text-blue-300">Total Files</p>
                      <p className="text-3xl font-bold text-blue-900 dark:text-blue-100">
                        {growth?.cumulative_files?.toLocaleString() || 0}
                      </p>
                    </div>
                    <BarChart3 className="w-10 h-10 text-blue-600 dark:text-blue-400" />
                  </div>

                  <div className="flex items-center justify-between p-4 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg">
                    <div>
                      <p className="text-sm text-purple-700 dark:text-purple-300">Total Chunks</p>
                      <p className="text-3xl font-bold text-purple-900 dark:text-purple-100">
                        {growth?.cumulative_chunks?.toLocaleString() || 0}
                      </p>
                    </div>
                    <BarChart3 className="w-10 h-10 text-purple-600 dark:text-purple-400" />
                  </div>

                  {growth?.growth_by_date && growth.growth_by_date.length > 0 && (
                    <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                        Recent Activity ({growth.growth_by_date.length} days)
                      </p>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Most active: {growth.growth_by_date[0]?.date || 'N/A'} ({growth.growth_by_date[0]?.syncs_count || 0} syncs)
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};
