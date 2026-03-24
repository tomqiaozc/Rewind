"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquare, RotateCcw, Trash2, Zap } from "lucide-react";
import { listTrash, restoreSession, batchOperation } from "@/lib/api";
import type { SessionListItem } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import { formatRelativeTime, formatTokens } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function TrashPage() {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoringIds, setRestoringIds] = useState<Set<string>>(new Set());
  const [restoringAll, setRestoringAll] = useState(false);

  const fetchTrash = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTrash({ page, page_size: pageSize });
      setSessions(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchTrash();
  }, [fetchTrash]);

  const handleRestore = useCallback(
    async (e: React.MouseEvent, sessionId: string) => {
      e.preventDefault();
      e.stopPropagation();
      setRestoringIds((prev) => new Set(prev).add(sessionId));
      try {
        await restoreSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        setTotal((prev) => prev - 1);
      } catch {
        // Restore failed — remove loading state
      } finally {
        setRestoringIds((prev) => {
          const next = new Set(prev);
          next.delete(sessionId);
          return next;
        });
      }
    },
    [],
  );

  const handleRestoreAll = useCallback(async () => {
    if (sessions.length === 0) return;
    setRestoringAll(true);
    try {
      await batchOperation({
        session_ids: sessions.map((s) => s.id),
        action: "restore",
      });
      setSessions([]);
      setTotal(0);
      setPage(1);
    } catch {
      // Batch restore failed
    } finally {
      setRestoringAll(false);
    }
  }, [sessions]);

  const totalPages = Math.ceil(total / pageSize);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load trash</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Trash</h1>
          <p className="text-muted-foreground">
            Deleted sessions that can be restored
          </p>
        </div>
        {!loading && sessions.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            disabled={restoringAll}
            onClick={handleRestoreAll}
          >
            <RotateCcw className="mr-2 size-4" />
            {restoringAll ? "Restoring..." : "Restore All"}
          </Button>
        )}
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
            <Trash2 className="size-10 text-muted-foreground/40 mb-3" />
            <p className="text-muted-foreground">Trash is empty</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center gap-4 rounded-lg border p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate font-medium">
                    {session.title || session.session_key}
                  </p>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="secondary" className="text-xs">
                    {SOURCE_LABELS[session.source] || session.source}
                  </Badge>
                  <span>
                    Deleted {formatRelativeTime(session.last_message_at || session.created_at)}
                  </span>
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
                <Button
                  variant="outline"
                  size="sm"
                  disabled={restoringIds.has(session.id)}
                  onClick={(e) => handleRestore(e, session.id)}
                >
                  <RotateCcw className="mr-2 size-3.5" />
                  {restoringIds.has(session.id) ? "Restoring..." : "Restore"}
                </Button>
              </div>
            </div>
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
