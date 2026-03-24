"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Clock, MessageSquare, Star, Zap } from "lucide-react";
import { listSessions, getSessionFilters } from "@/lib/api";
import type { SessionListItem, FilterValues } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import {
  formatRelativeTime,
  formatDuration,
  formatTokens,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterValues | null>(null);
  const [source, setSource] = useState("");
  const [project, setProject] = useState("");

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSessions({
        page,
        page_size: pageSize,
        source: source || undefined,
        project: project || undefined,
        sort_by: "last_message_at",
        sort_order: "desc",
      });
      setSessions(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, source, project]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    getSessionFilters()
      .then(setFilters)
      .catch(() => {});
  }, []);

  const totalPages = Math.ceil(total / pageSize);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load sessions</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Sessions</h1>
        <p className="text-muted-foreground">
          Browse and search your AI coding sessions
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All sources</option>
          {filters?.sources.map((s) => (
            <option key={s} value={s}>
              {SOURCE_LABELS[s] || s}
            </option>
          ))}
        </select>
        <select
          value={project}
          onChange={(e) => {
            setProject(e.target.value);
            setPage(1);
          }}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All projects</option>
          {filters?.projects.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <span className="ml-auto text-sm text-muted-foreground">
          {total} session{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Session list */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-[88px] rounded-lg" />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">No sessions found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <Link
              key={session.id}
              href={`/dashboard/sessions/${session.id}`}
              className="flex items-center gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {session.is_starred && (
                    <Star className="size-4 fill-yellow-400 text-yellow-400" />
                  )}
                  <p className="truncate font-medium">
                    {session.title || session.session_key}
                  </p>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="secondary" className="text-xs">
                    {SOURCE_LABELS[session.source] || session.source}
                  </Badge>
                  {session.project_name && (
                    <span className="truncate">{session.project_name}</span>
                  )}
                  {session.model && (
                    <span className="truncate text-muted-foreground/70">
                      {session.model}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <div className="flex items-center gap-1" title="Messages">
                  <MessageSquare className="size-3.5" />
                  <span>{session.total_messages}</span>
                </div>
                <div className="flex items-center gap-1" title="Tokens">
                  <Zap className="size-3.5" />
                  <span>
                    {formatTokens(
                      session.total_input_tokens + session.total_output_tokens,
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-1" title="Duration">
                  <Clock className="size-3.5" />
                  <span>{formatDuration(session.duration_seconds)}</span>
                </div>
                <span className="w-24 text-right text-xs">
                  {formatRelativeTime(session.started_at)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
