"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FolderGit2, MessageSquare, Zap, Clock } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { listProjects } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { SOURCE_LABELS, SOURCE_COLORS } from "@/lib/types";
import {
  formatNumber,
  formatTokens,
  formatDuration,
  formatRelativeTime,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((err) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load projects</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="text-muted-foreground">
          Overview of your AI coding projects
        </p>
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : projects.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <RankingChart projects={projects} />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard key={project.project_name} project={project} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Project Card ──────────────────────────────────────────────────────

function ProjectCard({ project }: { project: ProjectSummary }) {
  const totalTokens = project.total_input_tokens + project.total_output_tokens;

  return (
    <Link
      href={`/dashboard/sessions?project=${encodeURIComponent(project.project_name)}`}
      className="group block"
    >
      <Card className="transition-colors group-hover:bg-muted/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderGit2 className="size-5 text-primary shrink-0" />
            <CardTitle className="truncate text-base font-semibold">
              {project.project_name}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <FolderGit2 className="size-3.5 shrink-0" />
              <span>
                {project.session_count}{" "}
                {project.session_count === 1 ? "session" : "sessions"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <MessageSquare className="size-3.5 shrink-0" />
              <span>{formatNumber(project.total_messages)} msgs</span>
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Zap className="size-3.5 shrink-0" />
              <span>{formatTokens(totalTokens)} tokens</span>
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Clock className="size-3.5 shrink-0" />
              <span>{formatDuration(project.total_duration_seconds)}</span>
            </div>
          </div>

          {/* Source badges */}
          {project.sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {project.sources.map((source) => (
                <Badge
                  key={source}
                  variant="outline"
                  className="text-xs"
                  style={{
                    borderColor: SOURCE_COLORS[source],
                    color: SOURCE_COLORS[source],
                  }}
                >
                  {SOURCE_LABELS[source] || source}
                </Badge>
              ))}
            </div>
          )}

          {/* Last activity */}
          <p className="text-xs text-muted-foreground">
            Last activity: {formatRelativeTime(project.last_session_at)}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

// ── Ranking Chart ─────────────────────────────────────────────────────

function RankingChart({ projects }: { projects: ProjectSummary[] }) {
  const chartData = projects
    .slice()
    .sort((a, b) => b.session_count - a.session_count)
    .slice(0, 10)
    .map((p) => ({
      name: p.project_name,
      sessions: p.session_count,
    }));

  const chartHeight = Math.max(200, chartData.length * 36);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Top Projects by Sessions</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
              width={140}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
            />
            <Bar
              dataKey="sessions"
              fill="hsl(var(--primary))"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-[250px] rounded-lg" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[200px] rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-16">
        <FolderGit2 className="size-12 text-muted-foreground/40" />
        <p className="mt-4 text-muted-foreground">No projects found.</p>
        <p className="mt-1 text-sm text-muted-foreground/70">
          Projects appear when sessions are synced with project metadata.
        </p>
      </CardContent>
    </Card>
  );
}
