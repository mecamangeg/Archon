import { Activity, Brain, TrendingUp, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type React from "react";
import { useState } from "react";
import { glassmorphism } from "../features/ui/primitives/styles";
import { cn } from "../lib/utils";

// Types
interface LearningMetrics {
  total_patterns: number;
  auto_approved: number;
  success_rate: number;
  last_cycle: string;
}

interface Pattern {
  id: string;
  error_signature: string;
  platform: string;
  tool: string;
  success_rate: number;
  usage_count: number;
  created_at: string;
  auto_approved: boolean;
}

interface ActivityItem {
  type: "auto_approved" | "pending_review" | "declining";
  timestamp: string;
  pattern_id: string;
  signature: string;
  evidence: {
    successes: number;
    failures: number;
    success_rate: number;
  };
}

// Mock API functions (replace with real API calls)
const fetchMetrics = async (): Promise<LearningMetrics> => {
  // TODO: Replace with actual API call to archon-skill backend
  // const response = await fetch('http://localhost:8181/api/cic/dashboard/metrics');
  // return response.json();

  // Mock data
  return {
    total_patterns: 31,
    auto_approved: 28,
    success_rate: 0.942,
    last_cycle: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  };
};

const fetchRecentActivity = async (): Promise<ActivityItem[]> => {
  // TODO: Replace with actual API call
  // const response = await fetch('http://localhost:8181/api/cic/dashboard/activity?limit=10');
  // return response.json();

  // Mock data
  return [
    {
      type: "auto_approved",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      pattern_id: "1",
      signature: "ModuleNotFoundError: No module named 'requests'",
      evidence: { successes: 12, failures: 0, success_rate: 1.0 },
    },
    {
      type: "pending_review",
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      pattern_id: "2",
      signature: "PermissionError: [Errno 13] Permission denied",
      evidence: { successes: 4, failures: 1, success_rate: 0.8 },
    },
    {
      type: "declining",
      timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
      pattern_id: "3",
      signature: "Exit code 255",
      evidence: { successes: 18, failures: 7, success_rate: 0.72 },
    },
  ];
};

const fetchTopPatterns = async (): Promise<Pattern[]> => {
  // TODO: Replace with actual API call
  // const response = await fetch('http://localhost:8181/api/cic/patterns?limit=5&sort=usage');
  // return response.json();

  // Mock data
  return [
    {
      id: "1",
      error_signature: "ModuleNotFoundError: requests",
      platform: "windows",
      tool: "python",
      success_rate: 1.0,
      usage_count: 45,
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      auto_approved: true,
    },
    {
      id: "2",
      error_signature: "Exit code 255",
      platform: "all",
      tool: "bash",
      success_rate: 0.72,
      usage_count: 67,
      created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      auto_approved: true,
    },
    {
      id: "3",
      error_signature: "Path not found: settings.json",
      platform: "windows",
      tool: "read",
      success_rate: 0.95,
      usage_count: 23,
      created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      auto_approved: true,
    },
  ];
};

// Utility functions
const formatTimeAgo = (timestamp: string): string => {
  const now = new Date();
  const past = new Date(timestamp);
  const diffMs = now.getTime() - past.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

const formatSuccessRate = (rate: number): string => {
  return `${(rate * 100).toFixed(1)}%`;
};

// Components
const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: "up" | "down" | "stable";
}> = ({ title, value, subtitle, icon, trend }) => {
  return (
    <div
      className={cn(
        "p-6 rounded-xl",
        glassmorphism.background.subtle,
        "border border-gray-200 dark:border-zinc-800/50",
        "shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]",
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium text-gray-500 dark:text-zinc-400">{title}</div>
        <div className="text-gray-400 dark:text-zinc-500">{icon}</div>
      </div>
      <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1">{value}</div>
      {subtitle && (
        <div className="flex items-center gap-2">
          {trend && (
            <TrendingUp
              className={cn(
                "h-4 w-4",
                trend === "up" && "text-green-500",
                trend === "down" && "text-red-500 rotate-180",
                trend === "stable" && "text-gray-400",
              )}
            />
          )}
          <div className="text-sm text-gray-500 dark:text-zinc-400">{subtitle}</div>
        </div>
      )}
    </div>
  );
};

const ActivityFeed: React.FC<{ activities: ActivityItem[] }> = ({ activities }) => {
  const getActivityIcon = (type: ActivityItem["type"]) => {
    switch (type) {
      case "auto_approved":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "pending_review":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "declining":
        return <TrendingUp className="h-5 w-5 text-red-500 rotate-180" />;
    }
  };

  const getActivityTitle = (type: ActivityItem["type"]) => {
    switch (type) {
      case "auto_approved":
        return "Auto-approved";
      case "pending_review":
        return "Pending Review";
      case "declining":
        return "Declining Pattern";
    }
  };

  const getActivityColor = (type: ActivityItem["type"]) => {
    switch (type) {
      case "auto_approved":
        return "text-green-600 dark:text-green-400";
      case "pending_review":
        return "text-yellow-600 dark:text-yellow-400";
      case "declining":
        return "text-red-600 dark:text-red-400";
    }
  };

  return (
    <div className="space-y-3">
      {activities.map((activity, index) => (
        <div
          key={`${activity.pattern_id}-${index}`}
          className={cn(
            "p-4 rounded-lg",
            glassmorphism.background.base,
            "border border-gray-200 dark:border-zinc-800/50",
            "hover:shadow-lg transition-shadow duration-200",
            "cursor-pointer",
          )}
        >
          <div className="flex items-start gap-3">
            <div className="mt-0.5">{getActivityIcon(activity.type)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className={cn("text-sm font-medium", getActivityColor(activity.type))}>
                  {getActivityTitle(activity.type)}
                </span>
                <span className="text-xs text-gray-500 dark:text-zinc-500">
                  {formatTimeAgo(activity.timestamp)}
                </span>
              </div>
              <div className="text-sm text-gray-900 dark:text-white mb-2 truncate">
                {activity.signature}
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-zinc-400">
                <span>
                  {activity.evidence.successes} successes, {activity.evidence.failures} failures
                </span>
                <span className="font-medium">{formatSuccessRate(activity.evidence.success_rate)}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const PatternTable: React.FC<{ patterns: Pattern[] }> = ({ patterns }) => {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-zinc-800/50">
      <table className="w-full">
        <thead
          className={cn(
            "text-xs font-medium text-gray-500 dark:text-zinc-400 uppercase",
            glassmorphism.background.base,
          )}
        >
          <tr>
            <th className="px-4 py-3 text-left">Error Signature</th>
            <th className="px-4 py-3 text-left">Platform</th>
            <th className="px-4 py-3 text-left">Tool</th>
            <th className="px-4 py-3 text-right">Success Rate</th>
            <th className="px-4 py-3 text-right">Used</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-zinc-800/50">
          {patterns.map((pattern) => (
            <tr
              key={pattern.id}
              className={cn(
                glassmorphism.background.subtle,
                "hover:bg-white/50 dark:hover:bg-white/5 transition-colors cursor-pointer",
              )}
            >
              <td className="px-4 py-3 text-sm text-gray-900 dark:text-white max-w-xs truncate">
                {pattern.error_signature}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 dark:text-zinc-400 capitalize">
                {pattern.platform}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 dark:text-zinc-400 capitalize">
                {pattern.tool}
              </td>
              <td
                className={cn(
                  "px-4 py-3 text-sm font-medium text-right",
                  pattern.success_rate >= 0.9
                    ? "text-green-600 dark:text-green-400"
                    : pattern.success_rate >= 0.7
                      ? "text-yellow-600 dark:text-yellow-400"
                      : "text-red-600 dark:text-red-400",
                )}
              >
                {formatSuccessRate(pattern.success_rate)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 dark:text-zinc-400 text-right">
                {pattern.usage_count}x
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export function ArchonSkillPage() {
  const [selectedTab, setSelectedTab] = useState<"dashboard" | "patterns" | "analytics">("dashboard");

  // Queries
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["cic-metrics"],
    queryFn: fetchMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: activities, isLoading: activitiesLoading } = useQuery({
    queryKey: ["cic-activity"],
    queryFn: fetchRecentActivity,
    refetchInterval: 30000,
  });

  const { data: topPatterns, isLoading: patternsLoading } = useQuery({
    queryKey: ["cic-top-patterns"],
    queryFn: fetchTopPatterns,
    refetchInterval: 60000, // Refresh every minute
  });

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Archon-Skill Learning System
            </h1>
            <p className="text-gray-500 dark:text-zinc-400">
              Monitor CIC self-learning patterns and system health
            </p>
          </div>
          <Brain className="h-12 w-12 text-blue-500" />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-gray-200 dark:border-zinc-800">
          <button
            onClick={() => setSelectedTab("dashboard")}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors relative",
              selectedTab === "dashboard"
                ? "text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300",
            )}
          >
            Dashboard
            {selectedTab === "dashboard" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
          <button
            onClick={() => setSelectedTab("patterns")}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors relative",
              selectedTab === "patterns"
                ? "text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300",
            )}
          >
            Patterns
            {selectedTab === "patterns" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
          <button
            onClick={() => setSelectedTab("analytics")}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors relative",
              selectedTab === "analytics"
                ? "text-blue-600 dark:text-blue-400"
                : "text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300",
            )}
          >
            Analytics
            {selectedTab === "analytics" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
            )}
          </button>
        </div>

        {/* Dashboard Tab */}
        {selectedTab === "dashboard" && (
          <div className="space-y-6">
            {/* Metrics Cards */}
            {metricsLoading ? (
              <div className="text-center py-8 text-gray-500 dark:text-zinc-400">Loading metrics...</div>
            ) : metrics ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Total Patterns"
                  value={metrics.total_patterns}
                  subtitle="Learned patterns"
                  icon={<Brain className="h-5 w-5" />}
                  trend="up"
                />
                <MetricCard
                  title="Auto-Approved"
                  value={metrics.auto_approved}
                  subtitle={`${((metrics.auto_approved / metrics.total_patterns) * 100).toFixed(0)}% of total`}
                  icon={<CheckCircle className="h-5 w-5" />}
                  trend="up"
                />
                <MetricCard
                  title="Success Rate"
                  value={formatSuccessRate(metrics.success_rate)}
                  subtitle="Overall confidence"
                  icon={<Activity className="h-5 w-5" />}
                  trend="stable"
                />
                <MetricCard
                  title="Last Cycle"
                  value={formatTimeAgo(metrics.last_cycle)}
                  subtitle="Learning activity"
                  icon={<Clock className="h-5 w-5" />}
                />
              </div>
            ) : null}

            {/* Recent Activity */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h2>
              {activitiesLoading ? (
                <div className="text-center py-8 text-gray-500 dark:text-zinc-400">Loading activity...</div>
              ) : activities && activities.length > 0 ? (
                <ActivityFeed activities={activities} />
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-zinc-400">No recent activity</div>
              )}
            </div>

            {/* Top Patterns */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Most Used Patterns
              </h2>
              {patternsLoading ? (
                <div className="text-center py-8 text-gray-500 dark:text-zinc-400">Loading patterns...</div>
              ) : topPatterns && topPatterns.length > 0 ? (
                <PatternTable patterns={topPatterns} />
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-zinc-400">No patterns found</div>
              )}
            </div>
          </div>
        )}

        {/* Patterns Tab */}
        {selectedTab === "patterns" && (
          <div className="text-center py-16">
            <Brain className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Pattern Explorer Coming Soon
            </h3>
            <p className="text-gray-500 dark:text-zinc-400 max-w-md mx-auto">
              Full pattern explorer with filters, search, and detailed evidence will be available in the next
              update.
            </p>
          </div>
        )}

        {/* Analytics Tab */}
        {selectedTab === "analytics" && (
          <div className="text-center py-16">
            <Activity className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Analytics Dashboard Coming Soon
            </h3>
            <p className="text-gray-500 dark:text-zinc-400 max-w-md mx-auto">
              Detailed analytics with charts, trends, and insights will be available in the next update.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
