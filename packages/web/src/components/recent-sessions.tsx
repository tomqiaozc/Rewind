"use client";

import Link from "next/link";
import { Clock, MessageSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SessionListItem } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import { formatRelativeTime, formatDuration } from "@/lib/format";

interface RecentSessionsProps {
  sessions: SessionListItem[];
}

export function RecentSessions({ sessions }: RecentSessionsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent Sessions</CardTitle>
      </CardHeader>
      <CardContent>
        {sessions.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No sessions yet. Run <code>rewind sync</code> to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <Link
                key={session.id}
                href={`/dashboard/sessions/${session.id}`}
                className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {session.title || session.session_key}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="text-xs">
                      {SOURCE_LABELS[session.source] || session.source}
                    </Badge>
                    {session.project_name && (
                      <span className="truncate">{session.project_name}</span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex flex-col items-end gap-1 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <MessageSquare className="size-3" />
                    {session.total_messages}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="size-3" />
                    {formatDuration(session.duration_seconds)}
                  </span>
                  <span>{formatRelativeTime(session.started_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
