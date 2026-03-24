"use client";

import { useEffect, useState } from "react";
import { getDashboardStats } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { StatsCards } from "@/components/stats-cards";
import { ActivityChart } from "@/components/activity-chart";
import { RecentSessions } from "@/components/recent-sessions";
import { SourceBreakdown } from "@/components/source-breakdown";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load dashboard</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your AI coding sessions
        </p>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[120px] rounded-lg" />
          ))}
        </div>
      ) : stats ? (
        <>
          <StatsCards stats={stats} />
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ActivityChart data={stats.sessions_by_day} />
            </div>
            <div>
              <SourceBreakdown data={stats.sessions_by_source} />
            </div>
          </div>
          <RecentSessions sessions={stats.recent_sessions} />
        </>
      ) : null}
    </div>
  );
}
