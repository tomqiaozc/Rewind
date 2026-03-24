"use client";

import { User, Bot, Wrench, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MessageDetail } from "@/lib/types";
import { formatTokens } from "@/lib/format";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageBubbleProps {
  message: MessageDetail;
  isActive: boolean;
  index: number;
}

const roleConfig = {
  user: {
    icon: User,
    label: "User",
    bg: "bg-primary/5 border-primary/20",
    activeBg: "bg-primary/10 border-primary/40",
  },
  assistant: {
    icon: Bot,
    label: "Assistant",
    bg: "bg-muted/50 border-muted-foreground/10",
    activeBg: "bg-muted border-muted-foreground/30",
  },
  tool: {
    icon: Wrench,
    label: "Tool",
    bg: "bg-accent/50 border-accent-foreground/10",
    activeBg: "bg-accent border-accent-foreground/30",
  },
  system: {
    icon: Info,
    label: "System",
    bg: "bg-secondary/50 border-secondary-foreground/10",
    activeBg: "bg-secondary border-secondary-foreground/30",
  },
} as const;

export function MessageBubble({ message, isActive, index }: MessageBubbleProps) {
  const role = message.role as keyof typeof roleConfig;
  const config = roleConfig[role] || roleConfig.assistant;
  const Icon = config.icon;

  return (
    <div
      id={`msg-${index}`}
      className={cn(
        "rounded-lg border p-4 transition-colors",
        isActive ? config.activeBg : config.bg,
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm">
          <Icon className="size-4" />
          <span className="font-medium">{config.label}</span>
          {message.tool_name && (
            <span className="text-xs text-muted-foreground">
              ({message.tool_name})
            </span>
          )}
          {message.tool_status && (
            <span
              className={cn(
                "text-xs",
                message.tool_status === "error"
                  ? "text-destructive"
                  : "text-muted-foreground",
              )}
            >
              [{message.tool_status}]
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {(message.input_tokens > 0 || message.output_tokens > 0) && (
            <span>
              {formatTokens(message.input_tokens)} / {formatTokens(message.output_tokens)} tokens
            </span>
          )}
          <span className="font-mono">#{message.ordinal}</span>
        </div>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none break-words">
        {message.content ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        ) : (
          <p className="italic text-muted-foreground">(empty message)</p>
        )}
      </div>
    </div>
  );
}
