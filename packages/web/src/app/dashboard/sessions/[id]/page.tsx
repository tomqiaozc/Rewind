"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  MessageSquare,
  Zap,
} from "lucide-react";
import { getSession } from "@/lib/api";
import type { SessionDetail } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import {
  formatDateTime,
  formatDuration,
  formatNumber,
  formatTokens,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageBubble } from "@/components/message-bubble";

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    getSession(id)
      .then(setSession)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // j/k keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!session) return;
      if (e.key === "j" && activeIndex < session.messages.length - 1) {
        setActiveIndex((i) => i + 1);
        document
          .getElementById(`msg-${activeIndex + 1}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      if (e.key === "k" && activeIndex > 0) {
        setActiveIndex((i) => i - 1);
        document
          .getElementById(`msg-${activeIndex - 1}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    [session, activeIndex],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[200px] rounded-lg" />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">
          {error || "Session not found"}
        </p>
        <Button variant="outline" className="mt-4" render={<Link href="/dashboard/sessions" />}>
          Back to sessions
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" render={<Link href="/dashboard/sessions" />}>
          <ArrowLeft className="size-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">
            {session.title || session.session_key}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="secondary">
              {SOURCE_LABELS[session.source] || session.source}
            </Badge>
            {session.project_name && <span>{session.project_name}</span>}
            {session.model && (
              <span className="text-muted-foreground/70">{session.model}</span>
            )}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <MessageSquare className="size-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Messages</p>
              <p className="text-sm font-medium">
                {formatNumber(session.total_messages)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Clock className="size-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Duration</p>
              <p className="text-sm font-medium">
                {formatDuration(session.duration_seconds)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Zap className="size-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Input Tokens</p>
              <p className="text-sm font-medium">
                {formatTokens(session.total_input_tokens)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Zap className="size-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Output Tokens</p>
              <p className="text-sm font-medium">
                {formatTokens(session.total_output_tokens)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Started: {formatDateTime(session.started_at)}</span>
        <Separator orientation="vertical" className="h-3" />
        <span>
          Last message: {formatDateTime(session.last_message_at)}
        </span>
      </div>

      <Separator />

      {/* Messages */}
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Use <kbd className="rounded border bg-muted px-1 py-0.5 text-xs font-mono">j</kbd> / <kbd className="rounded border bg-muted px-1 py-0.5 text-xs font-mono">k</kbd> to navigate messages
        </p>
        {session.messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isActive={i === activeIndex}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}
